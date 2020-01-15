# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
from press.press.doctype.bench.bench import Agent


class CustomDomain(Document):
	pass
	def validate(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_domain(self.name)
