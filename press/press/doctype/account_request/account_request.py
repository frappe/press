# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class AccountRequest(Document):
	def validate(self):
		if not self.user:
			self.create_new_user()

	def create_new_user(self):
		user_dict = {
			"doctype": "User",
			"first_name": self.first_name,
			"last_name": self.last_name,
			"new_password": self.password,
			"email": self.email,
			"send_welcome_email": 0,
			"roles": [{"role": "Press User"}],
		}
		self.user = frappe.get_doc(user_dict).insert(ignore_permissions=True).name
