# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""A user of a product site signs in on /site-login with an emailed OTP."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, set_request

from press.api.site_login import send_otp, sync_product_site_user, verify_otp
from press.press.doctype.site.test_site import create_test_site

EMAIL = "site-user@example.com"
SITE_SECRET = "site-communication-secret"  # pragma: allowlist secret


def restore_local_after(test: FrappeTestCase, *attributes: str):
	"""patch.object cannot restore an attribute of a werkzeug Local, so do it here."""
	for attribute in attributes:
		if hasattr(frappe.local, attribute):
			test.addCleanup(setattr, frappe.local, attribute, getattr(frappe.local, attribute))
		else:
			test.addCleanup(
				lambda name=attribute: hasattr(frappe.local, name) and delattr(frappe.local, name)
			)


@patch.dict(frappe.conf, {"developer_mode": 0})
@patch.object(frappe, "sendmail", new=Mock())
class TestSiteLoginOtp(FrappeTestCase):
	def setUp(self):
		restore_local_after(self, "request_ip", "cookie_manager")
		frappe.local.request_ip = "127.0.0.1"
		frappe.local.cookie_manager = Mock()

	def tearDown(self):
		frappe.db.rollback()

	def session(self):
		return frappe.get_last_doc("Site User Session", {"user": EMAIL})

	def make_otp_older_by(self, delta: timedelta):
		frappe.db.set_value(
			"Site User Session", self.session().name, "otp_generated_at", now_datetime() - delta
		)

	def test_send_otp_mails_a_new_code_to_the_user(self):
		send_otp(EMAIL)

		session = self.session()
		self.assertTrue(session.otp)
		self.assertIn(session.otp, frappe.sendmail.call_args.kwargs["subject"])

	def test_send_otp_again_within_30_seconds_is_refused(self):
		send_otp(EMAIL)

		with self.assertRaisesRegex(frappe.ValidationError, "Please wait for 30 seconds"):
			send_otp(EMAIL)

	def test_verify_otp_with_the_mailed_code_verifies_the_session_and_sets_the_session_cookie(self):
		send_otp(EMAIL)
		session = self.session()

		verify_otp(EMAIL, session.otp)

		session.reload()
		self.assertEqual((session.verified, session.otp), (1, None))
		cookie_name, cookie_value = frappe.local.cookie_manager.set_cookie.call_args.args
		self.assertEqual((cookie_name, cookie_value), ("site_user_sid", session.session_id))

	def test_verify_otp_with_a_wrong_code_is_refused_and_leaves_the_session_unverified(self):
		send_otp(EMAIL)

		with self.assertRaisesRegex(frappe.ValidationError, "Invalid OTP"):
			verify_otp(EMAIL, "000000")

		self.assertEqual(self.session().verified, 0)
		frappe.local.cookie_manager.set_cookie.assert_not_called()

	def test_verify_otp_with_a_code_older_than_five_minutes_is_refused(self):
		send_otp(EMAIL)
		self.make_otp_older_by(timedelta(minutes=6))

		with self.assertRaisesRegex(frappe.ValidationError, "OTP is expired"):
			verify_otp(EMAIL, self.session().otp)

	def test_verify_otp_with_a_code_older_than_a_day_is_refused(self):
		send_otp(EMAIL)
		self.make_otp_older_by(timedelta(days=1, minutes=1))

		with self.assertRaisesRegex(frappe.ValidationError, "OTP is expired"):
			verify_otp(EMAIL, self.session().otp)

	def test_verify_otp_for_an_email_that_never_asked_for_a_code_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Invalid session"):
			verify_otp("someone-else@example.com", "111111")


class TestSyncProductSiteUser(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site()
		self.site.db_set("saas_communication_secret", SITE_SECRET)
		restore_local_after(self, "request")

	def tearDown(self):
		frappe.db.rollback()

	def sync(self, secret: str, enabled: int = 1):
		set_request(method="POST", headers={"X-Site": self.site.name, "X-Site-Token": secret})
		sync_product_site_user(user_info={"email": EMAIL, "enabled": enabled})

	def site_user_enabled(self):
		return frappe.db.get_value("Site User", {"site": self.site.name, "user": EMAIL}, "enabled")

	def test_sync_with_the_sites_secret_adds_the_user_to_the_site(self):
		self.sync(SITE_SECRET)

		self.assertEqual(self.site_user_enabled(), 1)

	def test_sync_again_disables_a_user_that_the_site_disabled(self):
		self.sync(SITE_SECRET)

		self.sync(SITE_SECRET, enabled=0)

		self.assertEqual(self.site_user_enabled(), 0)

	def test_sync_with_a_wrong_secret_is_refused_and_adds_no_user(self):
		with self.assertRaisesRegex(frappe.ValidationError, "The secret seems invalid"):
			self.sync("wrong-secret")

		self.assertIsNone(self.site_user_enabled())

	def test_sync_without_a_secret_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Invalid communication secret"):
			self.sync("")

		self.assertIsNone(self.site_user_enabled())
