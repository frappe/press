# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.press.doctype.agent_job.agent_job import Agent


class Site(Document):
	def validate(self):
		if not self.admin_password:
			self.admin_password = frappe.generate_hash(length=16)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		agent.new_site(self)

		server = frappe.get_all(
			"Server", filters={"name": self.server}, fields=["proxy_server"], limit=1
		)[0]

		agent = Agent(server.proxy_server, server_type="Proxy Server")
		agent.new_upstream_site(self.server, self.name)
