# Copyright (c) 2024, Frappe and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.user_2fa.user_2fa import User2FA


class TestUser2FA(FrappeTestCase):
	def test_generate_secret(self):
		recovery_codes = list(User2FA.generate_recovery_codes())
		self.assertEqual(len(recovery_codes), User2FA.recovery_codes_max)
		self.assertTrue(all(len(code) == User2FA.recovery_codes_length for code in recovery_codes))
		self.assertTrue(all(code.isupper() for code in recovery_codes))
