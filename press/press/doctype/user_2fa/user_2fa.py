# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import random
import string

import frappe
import frappe.utils
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

	# Maximum number of recovery codes.
	recovery_codes_max = 9

	# Length of each recovery code.
	recovery_codes_length = 16

	def validate(self):
		if self.enabled and not self.totp_secret:
			self.generate_secret()

	def generate_secret(self):
		import pyotp

		self.totp_secret = pyotp.random_base32()

	def generate_random_alphanum(length: int) -> str:
		if length < 2:
			raise ValueError("Length must be at least 2")

		letters = string.ascii_letters
		digits = string.digits
		all_chars = letters + digits
		# ensure at least one letter and one non-letter
		result = [random.choice(letters), random.choice(digits)]
		# fill the rest randomly
		result += [random.choice(all_chars) for _ in range(length - 2)]
		random.shuffle(result)
		return "".join(result).upper()

	@classmethod
	def generate_recovery_codes(self):
		counter = 0
		while counter < self.recovery_codes_max:
			code = self.generate_random_alphanum(self.recovery_codes_length)
			has_upper = code.isupper()
			has_digit = any(c.isdigit() for c in code)
			if has_upper and has_digit:
				counter += 1
				yield code

	def mark_recovery_codes_viewed(self):
		"""
		Mark recovery codes as viewed by updating the last viewed timestamp.
		Also, send an email notification to the user.
		"""

		# Update the time.
		self.recovery_codes_last_viewed_at = frappe.utils.now_datetime()

		# Send email notification.
		try:
			args = {
				"viewed_at": frappe.utils.format_datetime(self.recovery_codes_last_viewed_at),
				"link": frappe.utils.get_url("/dashboard/settings/profile"),
			}

			frappe.sendmail(
				recipients=[self.user],
				subject="Your 2FA Recovery Codes Were Viewed",
				template="2fa_recovery_codes_viewed",
				args=args,
			)
		except Exception:
			frappe.log_error("Failed to send recovery codes viewed notification email")


def yearly_2fa_recovery_code_reminder():
	"""Check and send yearly recovery code reminders"""

	# Construct email args.
	args = {
		"link": frappe.utils.get_url("/dashboard/settings/profile"),
	}

	# Get all users who have not viewed their recovery codes in the last year.
	users = frappe.get_all(
		"User 2FA",
		filters={
			"recovery_codes_last_viewed_at": [
				"<=",
				frappe.utils.add_to_date(frappe.utils.now_datetime(), years=-1),
			],
			"enabled": 1,
		},
		pluck="name",
	)

	for user in users:
		# Send mail.
		frappe.sendmail(
			recipients=[user],
			subject="Review Your 2FA Recovery Codes",
			template="2fa_recovery_codes_yearly_reminder",
			args=args,
		)
