# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.account import send_otp, verify_otp, verify_otp_and_login
from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils import otp as otp_purpose
from press.utils.otp import OneTimePassword


def code_that_was_mailed(send_otp_mail) -> str:
	"""`send_otp_mail(email, otp, for_login=...)` — the code is the second argument."""
	return send_otp_mail.call_args.args[1]


class TestOneTimePassword(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.code = OneTimePassword(otp_purpose.LOGIN, "someone@example.com")

	def tearDown(self):
		self.code.clear()
		frappe.db.rollback()

	def test_a_code_only_matches_the_purpose_it_was_issued_for(self):
		recovery = OneTimePassword(otp_purpose.TWO_FACTOR_RECOVERY, "someone@example.com")
		issued = self.code.generate()

		self.assertTrue(self.code.verify(issued))
		self.assertFalse(recovery.verify(issued))

	def test_a_cleared_code_stops_matching(self):
		issued = self.code.generate()
		self.code.clear()

		self.assertFalse(self.code.verify(issued))

	def test_nothing_matches_when_no_code_was_issued(self):
		self.assertFalse(OneTimePassword(otp_purpose.LOGIN, "nobody@example.com").verify("111111"))

	def test_the_code_itself_is_never_stored(self):
		issued = self.code.generate()

		self.assertNotIn(issued, str(frappe.cache.get_value(self.code.key)))

	def test_a_signup_code_lasts_as_long_as_the_link_it_is_mailed_with(self):
		signup = OneTimePassword(otp_purpose.SIGNUP, "some-account-request")

		self.assertEqual(signup.expires_in, 24 * 60 * 60)
		self.assertEqual(self.code.expires_in, 10 * 60)

	def test_a_purpose_with_no_declared_life_is_refused(self):
		with self.assertRaises(KeyError):
			OneTimePassword("something-new", "someone@example.com")


@patch("press.api.account.send_otp_mail")
class TestLoginOtp(FrappeTestCase):
	def setUp(self):
		super().setUp()
		# frappe's login attempt tracker keys on the request IP, and logging in
		# needs a login manager. Neither exists outside a request.
		frappe.local.request_ip = "127.0.0.1"
		frappe.local.login_manager = Mock(login_as=frappe.set_user)
		self.team = create_test_press_admin_team()

	def tearDown(self):
		frappe.set_user("Administrator")
		for purpose in (otp_purpose.LOGIN, otp_purpose.TWO_FACTOR_RECOVERY):
			OneTimePassword(purpose, self.team.user).clear()
		frappe.db.rollback()

	def test_login_works_without_an_account_request(self, send_otp_mail):
		"""The reported failure: user and team exist, the signup record does not."""
		frappe.db.delete("Account Request", {"email": self.team.user})

		send_otp(self.team.user)
		verify_otp_and_login(self.team.user, code_that_was_mailed(send_otp_mail))

		self.assertEqual(frappe.session.user, self.team.user)

	def test_send_otp_still_refuses_an_address_with_no_user(self, send_otp_mail):
		with self.assertRaisesRegex(Exception, "Please sign up first"):
			send_otp("no-such-person@example.com")

	def test_a_second_code_within_thirty_seconds_is_refused(self, send_otp_mail):
		send_otp(self.team.user)

		with self.assertRaisesRegex(Exception, "Please wait for 30 seconds"):
			send_otp(self.team.user)

	def test_a_recovery_code_does_not_log_anyone_in(self, send_otp_mail):
		"""Both used to be the same column, so either code worked for either flow."""
		send_otp(self.team.user, for_2fa_keys=True)

		with self.assertRaisesRegex(Exception, "Invalid OTP"):
			verify_otp_and_login(self.team.user, code_that_was_mailed(send_otp_mail))

	def test_a_signup_code_does_not_log_anyone_in(self, send_otp_mail):
		request = frappe.get_doc(
			{"doctype": "Account Request", "email": self.team.user, "team": self.team.name}
		).insert(ignore_permissions=True)

		with self.assertRaisesRegex(Exception, "Invalid OTP"):
			verify_otp_and_login(self.team.user, request.signup_otp.generate())

		request.signup_otp.clear()

	def test_a_login_code_is_spent_once(self, send_otp_mail):
		send_otp(self.team.user)
		issued = code_that_was_mailed(send_otp_mail)

		verify_otp_and_login(self.team.user, issued)
		with self.assertRaisesRegex(Exception, "Invalid OTP"):
			verify_otp_and_login(self.team.user, issued)


class TestSignupOtp(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.local.request_ip = "127.0.0.1"

	def tearDown(self):
		frappe.db.rollback()

	def create_signup(self) -> AccountRequest:
		with patch.object(AccountRequest, "send_verification_email"):
			return frappe.get_doc(
				{"doctype": "Account Request", "email": frappe.mock("email"), "send_email": True}
			).insert(ignore_permissions=True)

	def test_verifying_a_signup_returns_its_request_key(self):
		request = self.create_signup()
		issued = request.signup_otp.generate()

		key = verify_otp(request.name, issued)

		self.assertEqual(key, request.reload().request_key)
		self.assertFalse(request.signup_otp.verify(issued))

	def test_a_signup_code_is_scoped_to_its_own_request(self):
		mine = self.create_signup()
		theirs = self.create_signup()
		issued = mine.signup_otp.generate()

		with self.assertRaisesRegex(Exception, "Invalid OTP"):
			verify_otp(theirs.name, issued)

		mine.signup_otp.clear()
