# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe import frappe.utils
from frappe.model.document import Document


class User2FA(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.user_2fa_recovery_code.user_2fa_recovery_code import User2FARecoveryCode

		enabled: DF.Check
		last_verified_at: DF.Datetime | None
		recovery_codes: DF.Table[User2FARecoveryCode]
		recovery_codes_last_viewed_at: DF.Datetime | None
		totp_secret: DF.Password | None
		user: DF.Link | None
	# end: auto-generated types

	def validate(self):
		if self.enabled and not self.totp_secret:
			self.generate_secret()

	def generate_secret(self):
		import pyotp

		self.totp_secret = pyotp.random_base32()


def yearly_2fa_recovery_code_reminder():
	"""Check and send yearly recovery code reminders"""

	# Construct dashboard url.
	dashboard_url = frappe.utils.get_url("/dashboard/settings/profile")

	# Get all users who have not viewed their recovery codes in the last year.
	users = frappe.get_all(
		"User 2FA",
		filters={
			"recovery_codes_last_viewed_at": [
				"<=",
				frappe.utils.add_to_date(frappe.utils.now_datetime(), years=-1),
			],
			"user": ["!=", "Administrator"],
		},
		pluck="name",
	)

	for user in users:
		# Send mail.
		frappe.sendmail(
			recipients=[user],
			subject="Verify Your Recovery Codes",
			message=f"""
	           <p>It's been a year since you last reviewed your two-factor authentication recovery codes.</p>
	           <p>Please verify that you still have access to these codes. They are essential for account recovery if you lose access to your authentication device.</p>
	           <p><a href="{dashboard_url}">View your recovery codes</a></p>
	           """,
		)

		# Update recovery codes last viewed time.
		frappe.db.set_value("User 2FA", user, "recovery_codes_last_viewed_at", frappe.utils.now_datetime())
