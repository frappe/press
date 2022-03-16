# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SaasApp(Document):
	def autoname(self):
		self.name = self.app

	def get_app_versions(self):
		v = [ver.version_name for ver in self.app_versions]
		return v
