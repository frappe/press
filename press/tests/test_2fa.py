# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import datetime
from unittest.mock import patch

import frappe
import pyotp
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password

from press.api.account import (
	disable_2fa,
	enable_2fa,
	get_2fa_qr_code_url,
	get_2fa_recovery_codes,
	recover_2fa,
	reset_2fa_recovery_codes,
	send_otp,
)
from press.press.doctype.team.test_team import create_test_press_admin_team


class Test2FA(FrappeTestCase):
	password = "password"
	recovery_codes_max = 9
	recovery_codes_length = 16

	def setUp(self):
		super().setUp()

		with patch(
			"frappe.utils.now_datetime", return_value=datetime.datetime(2025, 8, 9, 12, 0, 0)
		):  # To avoid signup throttling issue
			self.team = create_test_press_admin_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits", remark="Test")
		self.team.payment_mode = "Prepaid Credits"
		self.team.save()

		frappe.set_user(self.team.user)
		update_password(self.team.user, self.password)

	def tearDown(self):
		super().tearDown()
		frappe.clear_cache()

		frappe.set_user("Administrator")

	def extract_secret_from_url(self, url):
		return url.split("secret=")[1].split("&")[0]

	def test_get_2fa_qr_code_url(self):
		url = get_2fa_qr_code_url()
		self.assertTrue(url.startswith("otpauth://totp/"))
		self.assertIn("secret=", url)

	def test_enable_correct_code(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		result = enable_2fa(code)
		self.assertTrue(result)
		self.assertIsInstance(result, list)

	def test_enable_wrong_code(self):
		get_2fa_qr_code_url()
		with self.assertRaises(frappe.ValidationError):
			enable_2fa("wrong_code")

	def test_disable_2fa_correct_code(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		self.assertIs(disable_2fa(code), None)

	def test_disable_2fa_wrong_code(self):
		get_2fa_qr_code_url()
		with self.assertRaises(frappe.ValidationError):
			disable_2fa("wrong_code")

	def test_recover_2fa_correct_code(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		recovery_codes = enable_2fa(code)
		recovery_code = recovery_codes.pop()
		result = recover_2fa(self.team.user, recovery_code)
		tfa_doc = frappe.get_doc("User 2FA", self.team.user)
		self.assertIs(result, None)
		self.assertEqual(tfa_doc.enabled, 0)

	def test_recover_2fa_wrong_code(self):
		get_2fa_qr_code_url()
		with self.assertRaises(frappe.ValidationError):
			recover_2fa(self.team.user, "wrong_code")

	def test_reset_recovery_codes(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		enable_2fa(code)
		result = reset_2fa_recovery_codes()
		self.assertTrue(result)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), self.recovery_codes_max)
		self.assertTrue(all(len(code) == self.recovery_codes_length for code in result))

	def test_get_recovery_codes_wrong_password(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		enable_2fa(code)
		with self.assertRaises(frappe.ValidationError):
			get_2fa_recovery_codes("wrong_password")

	def test_get_recovery_codes_correct_password(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		enable_2fa(code)
		send_otp(self.team.user, for_2fa_keys=True)
		verification_code = frappe.get_value(
			"Account Request", {"email": self.team.user}, "otp", order_by="creation desc"
		)
		recovery_codes = get_2fa_recovery_codes(verification_code)
		self.assertIsInstance(recovery_codes, list)
		self.assertLessEqual(len(recovery_codes), self.recovery_codes_max)
		self.assertTrue(all(len(code) == self.recovery_codes_length for code in recovery_codes))
