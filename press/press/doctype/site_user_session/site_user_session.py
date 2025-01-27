# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class SiteUserSession(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		otp: DF.Data | None
		session_id: DF.Data | None
		user: DF.Data | None
	# end: auto-generated types

	def send_otp(self):
		"""Send OTP to the user for site login."""

		import random

		self.otp = random.randint(100000, 999999)
		self.session_id = frappe.generate_hash()
		self.save()

		if frappe.conf.developer_mode:
			print(f"\nOTP for {self.user} for site login:")
			print()
			print(self.otp)
			print()
			return

		subject = f"{self.otp} - OTP for Frappe Cloud Site Login"
		args = {}

		args.update(
			{
				"otp": self.otp,
				"image_path": "https://github.com/frappe/gameplan/assets/9355208/447035d0-0686-41d2-910a-a3d21928ab94",
			}
		)

		frappe.sendmail(
			recipients=self.user,
			subject=subject,
			template="verify_account_for_site_login",
			args=args,
			now=True,
		)

	def verify_otp(self, otp):
		"""Verify OTP for site login."""
		import datetime

		if not self.otp:
			return frappe.throw("OTP is not set")
		if self.otp != otp:
			return frappe.throw("Invalid OTP")
		self.otp = None
		self.otp_verified_time = frappe.utils.now_datetime()
		self.save()

		expires = datetime.datetime.now() + datetime.timedelta(days=5)
		frappe.local.cookie_manager.set_cookie("site_session_id", self.session_id, expires=expires)
		return self.session_id
