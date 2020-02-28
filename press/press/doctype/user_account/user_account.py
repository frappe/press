# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class UserAccount(Document):
	def after_insert(self):
		user = frappe.new_doc("User")
		user.first_name = self.first_name
		user.last_name = self.last_name
		user.email = self.name
		user.append_roles("Press Admin")
		user.save(ignore_permissions=True)
		user.reset_password(send_email=True)
		self.user = user.name

