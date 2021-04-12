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
		self.send_verification_email()

	@frappe.whitelist()
	def send_verification_email(self):
		url = self.get_verification_url()

		if frappe.conf.developer_mode:
			print(f"\nSetup account URL for {self.email}:")
			print(url)
			print()
			return

		if self.erpnext:
			subject = "Set Up Your ERPNext Account"
			template = "erpnext_verify_account"
		else:
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

	def get_verification_url(self):
		if self.erpnext:
			return get_url(f"/setup-account?key={self.request_key}")
		return get_url(f"/dashboard/setup-account/{self.request_key}")
