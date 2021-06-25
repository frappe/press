import frappe

from unittest import TestCase
from unittest.mock import Mock, patch
from press.press.doctype.account_request.account_request import AccountRequest
from press.api.account import signup


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
