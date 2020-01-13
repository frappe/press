# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Bench(Document):
	def validate(self):
		if not self.candidate:
			candidate = frappe.get_all("Deploy Candidate", filters={"group": self.group})[0]
			self.candidate = candidate.name
		candidate = frappe.get_doc("Deploy Candidate", self.candidate)
		for release in candidate.apps:
			scrubbed = frappe.get_value("Frappe App", release.app, "scrubbed")
			self.append("apps", {"app": release.app, "scrubbed": scrubbed, "hash": release.hash})
