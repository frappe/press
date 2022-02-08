# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from press.agent import Agent

from press.overrides import get_permission_query_conditions_for_doctype


class SiteDomain(Document):
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
		certificate_status = frappe.db.get_value(
			"TLS Certificate", self.tls_certificate, "status"
		)
		if certificate_status == "Active":
			self.create_agent_request()
		elif certificate_status == "Failure":
			self.status = "Broken"
			self.save()

	def create_agent_request(self):
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.new_host(self)

	def create_remove_host_agent_request(self):
		server = frappe.db.get_value("Site", self.site, "server")
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
	}[job.status]

	if updated_status != domain_status:
		frappe.db.set_value("Site Domain", job.host, "status", updated_status)
		if updated_status == "Active":
			frappe.get_doc("Site", job.site).add_domain_to_config(job.host)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Site Domain"
)
