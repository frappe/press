# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils.verified_command import verify_request, get_signed_params
from frappe.utils import random_string, get_url


class UserAccount(Document):
	def after_insert(self):
		self.send_verification_email()

	def send_verification_email(self):
		signed_params = get_signed_params({"user": self.name})
		url = frappe.utils.get_url(
			"api/method/press.api.account.verify_account?" + signed_params
		)
		frappe.sendmail(
			recipients=self.name,
			subject="Verify your account",
			template="verify_account",
			args={"verify_link": url},
		)

	def create_user(self, password):
		user = frappe.new_doc("User")
		user.first_name = self.first_name
		user.last_name = self.last_name
		user.email = self.name
		user.new_password = password
		user.append_roles("Press Admin")
		user.flags.no_welcome_mail = True
		user.save(ignore_permissions=True)
		self.db_set("user", user.name)

	def on_trash(self):
		frappe.delete_doc("User", self.name)
