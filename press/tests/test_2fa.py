# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
import pyotp
from frappe.tests.utils import FrappeTestCase

from press.api.account import (
	disable_2fa,
	enable_2fa,
	get_2fa_qr_code_url,
	recover_2fa,
	reset_2fa_recovery_codes,
)


class Test2FA(FrappeTestCase):
	user = "Administrator"
	recovery_codes_max = 9
	recovery_codes_length = 16

	def setUp(self):
		frappe.set_user(self.user)

	def tearDown(self):
		# Clean up after tests if necessary
		pass

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
		with self.assertRaises(frappe.exceptions.ValidationError):
			enable_2fa("wrong_code")

	def test_disable_2fa_correct_code(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		self.assertIs(disable_2fa(code), None)

	def test_disable_2fa_wrong_code(self):
		get_2fa_qr_code_url()
		with self.assertRaises(frappe.exceptions.ValidationError):
			disable_2fa("wrong_code")

	def test_recover_2fa_correct_code(self):
		url = get_2fa_qr_code_url()
		secret = self.extract_secret_from_url(url)
		code = pyotp.totp.TOTP(secret).now()
		recovery_codes = enable_2fa(code)
		recovery_code = recovery_codes.pop()
		result = recover_2fa(self.user, recovery_code)
		tfa_doc = frappe.get_doc("User 2FA", self.user)
		self.assertIs(result, None)
		self.assertEqual(tfa_doc.enabled, 0)

	def test_recover_2fa_wrong_code(self):
		get_2fa_qr_code_url()
		with self.assertRaises(frappe.exceptions.ValidationError):
			recover_2fa(self.user, "wrong_code")

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
