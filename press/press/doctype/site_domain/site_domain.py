# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
import rq

from press.agent import Agent
from press.api.site import check_dns
from press.exceptions import AAAARecordExists, ConflictingCAARecord
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded


class SiteDomain(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dns_response: DF.Code | None
		dns_type: DF.Literal["A", "NS", "CNAME"]
		domain: DF.Data
		redirect_to_primary: DF.Check
		retry_count: DF.Int
		site: DF.Link
		status: DF.Literal["Pending", "In Progress", "Active", "Broken"]
		team: DF.Link
		tls_certificate: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ["domain", "status", "dns_type", "site", "redirect_to_primary"]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		domains = query.run(as_dict=1)
		if filters.site:
			host_name = frappe.db.get_value("Site", filters.site, "host_name")
			for domain in domains:
				if domain.domain == host_name:
					domain.primary = True
					break
			domains.sort(key=lambda domain: not domain.primary)
			return domains

	def after_insert(self):
		if not self.default:
			self.create_tls_certificate()

	def validate(self):
		if self.has_value_changed("redirect_to_primary"):
			if self.redirect_to_primary:
				self.setup_redirect_in_proxy()
			elif not self.is_new():
				self.remove_redirect_in_proxy()

	@property
	def default(self):
		return self.domain == self.site

	def setup_redirect_in_proxy(self):
		site = frappe.get_doc("Site", self.site)
		target = site.host_name
		if target == self.name:
			frappe.throw(
				"Primary domain can't be redirected.", exc=frappe.exceptions.ValidationError
			)
		site.set_redirects_in_proxy([self.name])

	def remove_redirect_in_proxy(self):
		site = frappe.get_doc("Site", self.site)
		site.unset_redirects_in_proxy([self.name])

	def setup_redirect(self):
		self.redirect_to_primary = True
		self.save()

	def remove_redirect(self):
		self.redirect_to_primary = False
		self.save()

	def create_tls_certificate(self):
		certificate = frappe.get_doc(
			{
				"doctype": "TLS Certificate",
				"wildcard": False,
				"domain": self.domain,
				"team": self.team,
			}
		).insert()
		self.tls_certificate = certificate.name
		self.save()

	def process_tls_certificate_update(self):
		certificate = frappe.db.get_value(
			"TLS Certificate", self.tls_certificate, ["status", "creation"], as_dict=True
		)
		if certificate.status == "Active":
			if frappe.utils.add_days(None, -1) > certificate.creation:
				# This is an old (older than 1 day) certificate, we are renewing it.
				# NGINX likely has a valid certificate, no need to reload.
				skip_reload = True
			else:
				skip_reload = False
			self.create_agent_request(skip_reload=skip_reload)
		elif certificate.status == "Failure":
			self.status = "Broken"
			self.save()

	def create_agent_request(self, skip_reload=False):
		server = frappe.db.get_value("Site", self.site, "server")
		is_standalone = frappe.db.get_value("Server", server, "is_standalone")
		if is_standalone:
			agent = Agent(server, server_type="Server")
		else:
			proxy_server = frappe.db.get_value("Server", server, "proxy_server")
			agent = Agent(proxy_server, server_type="Proxy Server")
		agent.new_host(self, skip_reload=skip_reload)

	def create_remove_host_agent_request(self):
		server = frappe.db.get_value("Site", self.site, "server")
		is_standalone = frappe.db.get_value("Server", server, "is_standalone")
		if is_standalone:
			agent = Agent(server, server_type="Server")
		else:
			proxy_server = frappe.db.get_value("Server", server, "proxy_server")
			agent = Agent(proxy_server, server_type="Proxy Server")
		agent.remove_host(self)

	def retry(self):
		self.status = "Pending"
		self.retry_count += 1
		self.save()
		if self.tls_certificate:
			certificate = frappe.get_doc("TLS Certificate", self.tls_certificate)
			certificate.obtain_certificate()
		else:
			self.create_tls_certificate()

	def on_trash(self):
		if self.domain == frappe.db.get_value("Site", self.site, "host_name"):
			frappe.throw(
				msg="Primary domain cannot be deleted", exc=frappe.exceptions.LinkExistsError
			)

		self.disavow_agent_jobs()
		if not self.default:
			self.create_remove_host_agent_request()
		elif self.redirect_to_primary:
			self.create_remove_host_agent_request()
		if self.status == "Active":
			self.remove_domain_from_site_config()

	def after_delete(self):
		self.delete_tls_certificate()

	def delete_tls_certificate(self):
		frappe.delete_doc("TLS Certificate", self.tls_certificate)

	def disavow_agent_jobs(self):
		jobs = frappe.get_all("Agent Job", filters={"host": self.name})
		for job in jobs:
			frappe.db.set_value("Agent Job", job.name, "host", None)

	def remove_domain_from_site_config(self):
		site_doc = frappe.get_doc("Site", self.site)
		if site_doc.status == "Archived":
			return
		site_doc.remove_domain_from_config(self.domain)


def process_new_host_job_update(job):
	domain_status = frappe.get_value("Site Domain", job.host, "status")

	updated_status = {
		"Pending": "Pending",
		"Running": "In Progress",
		"Success": "Active",
		"Failure": "Broken",
		"Delivery Failure": "Broken",
	}[job.status]

	if updated_status != domain_status:
		frappe.db.set_value("Site Domain", job.host, "status", updated_status)
		if updated_status == "Active":
			frappe.get_doc("Site", job.site).add_domain_to_config(job.host)


def update_dns_type():
	domains = frappe.get_all(
		"Site Domain",
		filters={"tls_certificate": ("is", "set")},  # Don't query wildcard subdomains
		fields=["name", "domain", "dns_type", "site"],
	)
	for domain in domains:
		if has_job_timeout_exceeded():
			return
		try:
			response = check_dns(domain.site, domain.domain)
			dns_type = "A" if response["type"] == "AAAA" else response["type"]
			if response["matched"] and dns_type != domain.dns_type:
				frappe.db.set_value(
					"Site Domain", domain.name, "dns_type", dns_type, update_modified=False
				)
			pretty_response = json.dumps(response, indent=4, default=str)
			frappe.db.set_value(
				"Site Domain", domain.name, "dns_response", pretty_response, update_modified=False
			)
			frappe.db.commit()
		except AAAARecordExists:
			pass
		except ConflictingCAARecord:
			pass
		except rq.timeouts.JobTimeoutException:
			return
		except Exception:
			frappe.db.rollback()
			log_error("DNS Check Failed", domain=domain)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Site Domain"
)
