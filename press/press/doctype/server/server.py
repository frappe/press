# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

# import frappe
from frappe.model.document import Document
from press.press.doctype.bench.bench import Agent


class Server(Document):
	def validate(self):
	def ping(self):
		agent = Agent(self)
		return agent.ping()
