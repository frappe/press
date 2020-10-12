# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.agent import Agent


class SiteDomain(Document):
	def after_insert(self):
		self.create_tls_certificate()

	def setup_redirect(self, target):
		self.redirect_to_primary = True
		self.save()
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.setup_redirect(self, target)

	def remove_redirect(self):
		self.redirect_to_primary = False
		self.save()
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.remove_redirect(self)

	def create_tls_certificate(self):
		if self.domain == self.site:
			return
		certificate = frappe.get_doc(
			{"doctype": "TLS Certificate", "wildcard": False, "domain": self.domain}
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
		self.disavow_agent_jobs()
		self.create_remove_host_agent_request()
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
