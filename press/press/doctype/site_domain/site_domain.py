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

	def create_tls_certificate(self):
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
		agent.ping()
		agent.new_host(self)

	def retry(self):
		self.status = "Pending"
		self.retry_count += 1
		self.save()
		if self.tls_certificate:
			certificate = frappe.get_doc("TLS Certificate", self.tls_certificate)
			certificate.obtain_certificate()
		else:
			self.create_tls_certificate()


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
			frappe.get_doc("Site", job.site).set_host_name(job.host)
