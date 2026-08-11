# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import patch

import frappe
import frappe.utils
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.user_2fa.user_2fa import (
	User2FA,
	send_2fa_recovery_code_reminders,
	unsubscribe_from_recovery_code_reminders,
	users_due_for_recovery_code_reminder,
)


def create_test_user_2fa(user: str, recovery_codes_last_viewed_at: str | None = None) -> User2FA:
	"""Create a User 2FA doc with 2FA turned on."""
	return frappe.get_doc(
		{
			"doctype": "User 2FA",
			"user": user,
			"enabled": 1,
			"recovery_codes_last_viewed_at": recovery_codes_last_viewed_at,
		}
	).insert(ignore_permissions=True)


class TestUser2FA(FrappeTestCase):
	def test_generate_secret(self):
		recovery_codes = list(User2FA.generate_recovery_codes())
		self.assertEqual(len(recovery_codes), User2FA.recovery_codes_max)
		self.assertTrue(all(len(code) == User2FA.recovery_codes_length for code in recovery_codes))
		self.assertTrue(all(code.isupper() for code in recovery_codes))


class Test2FARecoveryCodeReminders(FrappeTestCase):
	def setUp(self):
		self.team = create_test_team()
		self.user = self.team.user
		self.add_team_member(self.team, self.user)
		create_test_user_2fa(
			self.user,
			frappe.utils.add_to_date(frappe.utils.now_datetime(), years=-2),
		)

	def tearDown(self):
		frappe.db.rollback()

	def add_team_member(self, team, user: str):
		team.append("team_members", {"user": user})
		team.save(ignore_permissions=True)

	def test_reminder_is_due_for_enabled_user_of_an_enabled_team(self):
		self.assertIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_not_due_for_disabled_user(self):
		frappe.db.set_value("User", self.user, "enabled", 0)
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_not_due_when_every_team_of_the_user_is_disabled(self):
		frappe.db.set_value("Team", self.team.name, "enabled", 0)
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_due_when_user_still_has_one_enabled_team(self):
		other_team = create_test_team()
		self.add_team_member(other_team, self.user)
		frappe.db.set_value("Team", self.team.name, "enabled", 0)
		self.assertIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_not_due_for_recently_viewed_recovery_codes(self):
		frappe.db.set_value(
			"User 2FA", self.user, "recovery_codes_last_viewed_at", frappe.utils.now_datetime()
		)
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_not_due_when_2fa_is_disabled(self):
		frappe.db.set_value("User 2FA", self.user, "enabled", 0)
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_due_when_recovery_codes_were_never_viewed(self):
		self.mark_recovery_codes_never_viewed(
			created_at=frappe.utils.add_to_date(frappe.utils.now_datetime(), years=-2)
		)
		self.assertIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_not_due_when_2fa_was_turned_on_recently_without_viewing(self):
		self.mark_recovery_codes_never_viewed(created_at=frappe.utils.now_datetime())
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def mark_recovery_codes_never_viewed(self, created_at):
		frappe.db.set_value(
			"User 2FA",
			self.user,
			{"recovery_codes_last_viewed_at": None, "creation": created_at},
		)

	def test_no_mail_is_sent_to_a_disabled_user(self):
		frappe.db.set_value("User", self.user, "enabled", 0)
		self.assertNotIn([self.user], self.recipients_of_reminder_mails())

	def test_mail_is_sent_to_an_enabled_user(self):
		self.assertIn([self.user], self.recipients_of_reminder_mails())

	def recipients_of_reminder_mails(self) -> list[list[str]]:
		with patch.object(frappe, "sendmail") as sendmail:
			send_2fa_recovery_code_reminders()
		return [call.kwargs["recipients"] for call in sendmail.call_args_list]

	def test_reminder_is_not_due_within_a_month_of_the_last_one(self):
		self.mark_reminded_at(frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-29))
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def test_reminder_is_due_again_a_month_after_the_last_one(self):
		self.mark_reminded_at(frappe.utils.add_to_date(frappe.utils.now_datetime(), months=-1, days=-1))
		self.assertIn(self.user, users_due_for_recovery_code_reminder())

	def mark_reminded_at(self, reminded_at):
		frappe.db.set_value("User 2FA", self.user, "recovery_codes_last_reminded_at", reminded_at)

	def test_sending_a_reminder_records_when_it_went_out(self):
		self.recipients_of_reminder_mails()
		self.assertIsNotNone(frappe.db.get_value("User 2FA", self.user, "recovery_codes_last_reminded_at"))

	def test_a_second_run_on_the_same_day_sends_no_mail(self):
		self.recipients_of_reminder_mails()
		self.assertEqual(self.recipients_of_reminder_mails(), [])

	def test_reminder_is_not_due_for_an_unsubscribed_user(self):
		self.unsubscribe()
		self.assertNotIn(self.user, users_due_for_recovery_code_reminder())

	def test_no_mail_is_sent_to_an_unsubscribed_user(self):
		self.unsubscribe()
		self.assertNotIn([self.user], self.recipients_of_reminder_mails())

	def unsubscribe(self):
		with patch.object(frappe.db, "commit"):
			unsubscribe_from_recovery_code_reminders(self.user)

	def test_unsubscribing_marks_the_user_as_unsubscribed(self):
		self.unsubscribe()
		self.assertTrue(
			frappe.db.get_value("User 2FA", self.user, "unsubscribed_from_recovery_code_reminders")
		)
