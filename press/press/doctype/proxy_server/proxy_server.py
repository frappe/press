# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
from press.press.doctype.agent_job.agent_job import Agent


class ProxyServer(Document):
	def ping(self):
		agent = Agent(self, server_type="Proxy Server")
		return agent.ping()
