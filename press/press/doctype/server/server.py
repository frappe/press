# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

# import frappe
from frappe.model.document import Document
from press.agent import Agent


class Server(Document):
	def add_upstream_to_proxy(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_server(self.name)

	def ping(self):
		agent = Agent(self.name)
		return agent.ping()

	def update_agent(self):
		agent = Agent(self.name)
		return agent.update()

def process_new_server_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Server", job.upstream, "is_upstream_setup", True)
