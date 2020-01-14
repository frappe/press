# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from press.press.doctype.agent_job.agent_job import Agent


class Site(Document):
	def validate(self):
		if not self.password:
			self.password = frappe.generate_hash(length=16)
		agent = Agent(self.server)
		agent.new_site(self)
