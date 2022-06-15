# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

EXPIRES_IN_MINUTES = 10


class SaasRemoteLogin(Document):
	def before_insert(self):
		self.expires_on = frappe.utils.add_to_date(None, minutes=EXPIRES_IN_MINUTES)
