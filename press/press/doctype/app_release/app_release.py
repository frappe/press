# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class AppRelease(Document):
	def after_insert(self):
		self.create_deploy_candidates()
		
	def create_deploy_candidates(self):
		for group_app in frappe.get_all(
			"Release Group Frappe App", fields=["parent"], filters={"app": self.app}
		):
			group = frappe.get_doc("Release Group", group_app.parent)
			group.create_deploy_candidate()
