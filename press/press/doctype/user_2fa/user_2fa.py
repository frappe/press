# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import random
import string

import frappe
import frappe.utils
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce
from frappe.rate_limiter import rate_limit
from frappe.utils.verified_command import verify_request

# Where the unsubscribe link in the reminder mail points.
UNSUBSCRIBE_METHOD = (
	"/api/method/press.press.doctype.user_2fa.user_2fa.unsubscribe_from_recovery_code_reminders"
)


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
		recovery_codes_last_reminded_at: DF.Datetime | None
		recovery_codes_last_viewed_at: DF.Datetime | None
		totp_secret: DF.Password | None
		unsubscribed_from_recovery_code_reminders: DF.Check
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


def send_2fa_recovery_code_reminders():
	"""Remind users to review recovery codes they haven't looked at in a year."""

	for user in users_due_for_recovery_code_reminder():
		send_recovery_code_reminder(user)


def send_recovery_code_reminder(user: str):
	"""Mail one reminder and note when it went out, so the next one is a month away."""

	frappe.sendmail(
		recipients=[user],
		subject="Review Your 2FA Recovery Codes",
		template="2fa_recovery_codes_yearly_reminder",
		args={"link": frappe.utils.get_url("/dashboard/settings/profile")},
		reference_doctype="User 2FA",
		reference_name=user,
		unsubscribe_message="Stop these reminders",
		unsubscribe_method=UNSUBSCRIBE_METHOD,
	)

	frappe.db.set_value("User 2FA", user, "recovery_codes_last_reminded_at", frappe.utils.now_datetime())


def users_due_for_recovery_code_reminder() -> list[str]:
	"""Users with 2FA on who haven't viewed their recovery codes in the last year.

	The joins drop users who can't reach the dashboard anyway — disabled ones,
	and those left without a single enabled team. Reminding them is noise.

	Codes that were never viewed fall back to when the record was created, so
	they're reminded too — a plain `<=` on the timestamp drops those NULLs.

	The job runs daily, but each user hears from us once a month at most, which
	is why the last reminder is tracked per user instead of running the job
	monthly — a failed run then retries the next day.
	"""

	TwoFA = frappe.qb.DocType("User 2FA")
	User = frappe.qb.DocType("User")
	TeamMember = frappe.qb.DocType("Team Member")
	Team = frappe.qb.DocType("Team")

	now = frappe.utils.now_datetime()
	last_viewed_at = Coalesce(TwoFA.recovery_codes_last_viewed_at, TwoFA.creation)
	last_reminded_at = TwoFA.recovery_codes_last_reminded_at

	return (
		frappe.qb.from_(TwoFA)
		.join(User)
		.on(User.name == TwoFA.user)
		.join(TeamMember)
		.on((TeamMember.user == TwoFA.user) & (TeamMember.parenttype == "Team"))
		.join(Team)
		.on(Team.name == TeamMember.parent)
		.select(TwoFA.user)
		.distinct()
		.where(TwoFA.enabled == 1)
		.where(User.enabled == 1)
		.where(Team.enabled == 1)
		.where(TwoFA.unsubscribed_from_recovery_code_reminders == 0)
		.where(last_viewed_at <= frappe.utils.add_to_date(now, years=-1))
		.where(last_reminded_at.isnull() | (last_reminded_at <= frappe.utils.add_to_date(now, months=-1)))
	).run(pluck=True)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def unsubscribe_from_recovery_code_reminders(email: str):
	"""Stop the reminders for a user, from the link in the reminder mail."""

	# The link is signed, so anything unsigned isn't ours.
	if not frappe.in_test and not verify_request():
		return None

	frappe.db.set_value("User 2FA", email, "unsubscribed_from_recovery_code_reminders", 1)
	frappe.db.commit()

	return frappe.respond_as_web_page(
		_("Unsubscribed"),
		_(
			"You will no longer be reminded to review your 2FA recovery codes. You can turn these reminders back on from your profile settings."
		),
		indicator_color="green",
	)
