# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team


class TestStripePaymentMethod(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()

	def tearDown(self):
		frappe.db.rollback()

	@patch("press.press.doctype.stripe_payment_method.stripe_payment_method.get_stripe")
	def test_set_default_raises_and_leaves_local_state_unchanged_when_stripe_call_fails(self, mock_stripe):
		mock_stripe.return_value.Customer.modify.side_effect = Exception("stripe unavailable")

		payment_method = frappe.get_doc(
			{
				"doctype": "Stripe Payment Method",
				"team": self.team.name,
				"stripe_customer_id": "cus_test123",
				"stripe_payment_method_id": "pm_test123",
			}
		).insert(ignore_permissions=True)

		self.assertRaisesRegex(Exception, "stripe unavailable", payment_method.set_default)

		payment_method.reload()
		self.assertEqual(payment_method.is_default, 0)
		self.assertEqual(frappe.db.get_value("Team", self.team.name, "default_payment_method"), None)

	@patch("press.press.doctype.stripe_payment_method.stripe_payment_method.get_stripe")
	def test_deleting_payment_method_detaches_it_from_stripe(self, mock_stripe):
		payment_method = frappe.get_doc(
			{
				"doctype": "Stripe Payment Method",
				"team": self.team.name,
				"stripe_customer_id": "cus_test123",
				"stripe_payment_method_id": "pm_test123",
			}
		).insert(ignore_permissions=True)

		payment_method.delete()

		mock_stripe.return_value.PaymentMethod.detach.assert_called_once_with("pm_test123")
		self.assertFalse(frappe.db.exists("Stripe Payment Method", payment_method.name))

	@patch("press.press.doctype.stripe_payment_method.stripe_payment_method.get_stripe")
	def test_deleting_payment_method_raises_when_stripe_detach_fails(self, mock_stripe):
		mock_stripe.return_value.PaymentMethod.detach.side_effect = Exception("stripe unavailable")

		payment_method = frappe.get_doc(
			{
				"doctype": "Stripe Payment Method",
				"team": self.team.name,
				"stripe_customer_id": "cus_test123",
				"stripe_payment_method_id": "pm_test123",
			}
		).insert(ignore_permissions=True)

		self.assertRaisesRegex(Exception, "stripe unavailable", payment_method.delete)
		mock_stripe.return_value.PaymentMethod.detach.assert_called_once_with("pm_test123")
