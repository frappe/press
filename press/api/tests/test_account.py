from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from press.api.account import signup, validate_pincode
from press.press.doctype.account_request.account_request import AccountRequest


class TestAccountApi(TestCase):
	"""End-to-End Tests for account/team creation via API"""

	def tearDown(self):
		frappe.db.rollback()

	def _fake_signup(self, email: str = "user@test.com") -> Mock:
		"""Call press.api.account.signup without sending verification mail."""
		with patch.object(AccountRequest, "send_verification_email") as mock_send_email:
			signup(email)
		return mock_send_email

	def test_account_request_is_created_from_signup(self):
		acc_req_count_before = frappe.db.count("Account Request")
		self._fake_signup()
		acc_req_count_after = frappe.db.count("Account Request")
		self.assertGreater(acc_req_count_after, acc_req_count_before)

	def test_pincode_is_correctly_set(self):
		"""Test if pincode is correctly set on account creation."""
		test_billing_details = frappe._dict(
			{
				"billing_name": "John Doe",
				"address": "Rose Street",
				"city": "Mumbai",
				"state": "Maharashtra",
				"postal_code": "40004",
				"country": "India",
			}
		)

		self.assertRaises(frappe.ValidationError, validate_pincode, test_billing_details)

		test_billing_details["postal_code"] = "400001"
		test_billing_details["state"] = "Karnataka"
		self.assertRaisesRegex(
			frappe.ValidationError,
			f"Postal Code {test_billing_details.postal_code} is not associated with {test_billing_details.state}",
			validate_pincode,
			test_billing_details,
		)
