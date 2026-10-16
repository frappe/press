# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from contextlib import contextmanager
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import add_days, today

from press.api.client import run_doc_method
from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.press_role.test_press_role import create_permission_role, create_user
from press.press.doctype.team.test_team import create_test_team

STRIPE_URL = "https://invoice.stripe.com/i/test-invoice"


def create_website_user() -> str:
	"""A dashboard user. System users skip every team and role check."""
	user = create_user(f"{frappe.generate_hash(length=8)}@example.com")
	user.add_roles("Press User", "Press Admin")
	return user.name


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class TestInvoicePaymentUrl(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.invoice = self.create_unpaid_stripe_invoice()
		self.member = create_website_user()
		self.team.append("team_members", {"user": self.member})
		self.team.save()
		self.role = create_permission_role(self.team.name)
		self.role.add_user(self.member)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_unpaid_stripe_invoice(self) -> Invoice:
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=add_days(today(), -10),
			period_end=today(),
		).insert()
		invoice.db_set(
			{
				"status": "Unpaid",
				"due_date": today(),
				"stripe_invoice_id": "in_test",
				"stripe_invoice_url": STRIPE_URL,
			}
		)
		return invoice

	@contextmanager
	def as_user(self, user: str):
		frappe.set_user(user)
		frappe.local._current_team = None
		frappe.local.request = frappe._dict(method="POST", headers={"X-Press-Team": self.team.name})
		try:
			yield
		finally:
			del frappe.local.request
			frappe.local._current_team = None
			frappe.set_user("Administrator")

	def payment_url(self) -> str:
		run_doc_method(dt="Invoice", dn=self.invoice.name, method="stripe_payment_url")
		return frappe.response.message

	def test_member_with_billing_role_gets_payment_url_for_the_team_invoice(self):
		self.role.db_set("allow_billing", 1)
		with self.as_user(self.member):
			self.assertEqual(self.payment_url(), STRIPE_URL)

	def test_member_with_admin_role_gets_payment_url_for_the_team_invoice(self):
		self.role.db_set("admin_access", 1)
		with self.as_user(self.member):
			self.assertEqual(self.payment_url(), STRIPE_URL)

	def test_member_without_billing_role_is_refused_the_payment_url(self):
		with (
			self.as_user(self.member),
			self.assertRaisesRegex(
				frappe.PermissionError, "You do not have permission to perform the action"
			),
		):
			self.payment_url()

	def test_user_outside_the_team_is_refused_the_payment_url(self):
		outsider = create_website_user()
		create_test_team().append("team_members", {"user": outsider}).parent_doc.save()
		with self.as_user(outsider), self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
			self.payment_url()
