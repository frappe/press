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
		otp_generated_at: DF.Datetime | None
		session_id: DF.Data | None
		user: DF.Data | None
		verified: DF.Check
	# end: auto-generated types

	def send_otp(self):
		"""Send OTP to the user for site login."""

		from press.utils.otp import generate_otp

		self.otp = generate_otp()
		self.session_id = frappe.generate_hash()
		self.otp_generated_at = frappe.utils.now_datetime()
		if frappe.conf.developer_mode and frappe.local.dev_server:
			self.otp = 111111
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
