# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import random_string, get_url


class AccountRequest(Document):
	def before_insert(self):
		if not self.team:
			self.team = self.email

		if not self.request_key:
			self.request_key = random_string(32)

		self.ip_address = frappe.local.request_ip

		url = get_url("/dashboard/#/setup-account/" + self.request_key)
		if frappe.conf.developer_mode:
			print()
			print(f'Setup account URL for {self.email}:')
			print(url)
			print()

		subject = "Verify your account"
		template = "verify_account"
		if self.invited_by and self.role != "Press Admin":
			subject = f"You are invited by {self.invited_by} to join Frappe Cloud"
			template = "invite_team_member"

		frappe.sendmail(
			recipients=self.email,
			subject=subject,
			template=template,
			args={"link": url},
			now=True,
		)
