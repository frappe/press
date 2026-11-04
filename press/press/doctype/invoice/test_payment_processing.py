# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import time
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, get_last_day, now_datetime, today

from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.invoice.payment_processing import clear_stale_payment_processing
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.suspend_sites import get_teams_with_unpaid_invoices
from press.press.doctype.team.test_team import create_test_team


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class TestPaymentProcessing(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.invoice = self._create_unpaid_invoice()

	def tearDown(self):
		frappe.db.rollback()

	def _create_unpaid_invoice(self) -> Invoice:
		last_month = add_months(today(), -1)
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			type="Subscription",
			period_start=get_first_day(last_month),
			period_end=get_last_day(last_month),
		).insert()
		frappe.db.set_value(
			"Invoice",
			invoice.name,
			{"status": "Unpaid", "stripe_invoice_id": f"in_test{frappe.generate_hash(length=10)}"},
		)
		invoice.reload()
		return invoice

	def _receive_stripe_webhook(self, event_type: str, stripe_object: dict):
		frappe.get_doc(
			doctype="Stripe Webhook Log",
			payload=frappe.as_json(
				{
					"id": f"evt_test{frappe.generate_hash(length=10)}",
					"type": event_type,
					"data": {"object": stripe_object},
				}
			),
		).insert()

	def _receive_payment_processing_webhook(self):
		self._receive_stripe_webhook(
			"payment_intent.processing",
			{
				"id": f"pi_test{frappe.generate_hash(length=10)}",
				"object": "payment_intent",
				"invoice": self.invoice.stripe_invoice_id,
				"status": "processing",
			},
		)

	def _receive_payment_event(self, event_type: str, payment_status: str, stripe_invoice: dict):
		frappe.get_doc(
			doctype="Stripe Payment Event",
			invoice=self.invoice.name,
			team=self.team.name,
			event_type=event_type,
			payment_status=payment_status,
			stripe_invoice_id=self.invoice.stripe_invoice_id,
			stripe_invoice_object=frappe.as_json(stripe_invoice),
		).insert()

	def _payment_processing_since(self):
		return frappe.db.get_value("Invoice", self.invoice.name, "payment_processing_since")

	def test_payment_intent_processing_webhook_marks_invoice_payment_processing(self):
		self._receive_payment_processing_webhook()
		self.assertIsNotNone(self._payment_processing_since())

	def test_payment_processing_webhook_does_not_mark_paid_invoice(self):
		frappe.db.set_value("Invoice", self.invoice.name, "status", "Paid")
		self._receive_payment_processing_webhook()
		self.assertIsNone(self._payment_processing_since())

	def test_failed_invoice_payment_clears_payment_processing_so_customer_can_pay_again(self):
		self._receive_payment_processing_webhook()
		self._receive_payment_event("Failed", "Unpaid", {"attempt_count": 1})

		self.assertIsNone(self._payment_processing_since())
		self.assertEqual(frappe.db.get_value("Invoice", self.invoice.name, "status"), "Unpaid")

	def test_succeeded_invoice_payment_marks_invoice_paid_and_clears_payment_processing(self):
		self._receive_payment_processing_webhook()
		self._receive_payment_event(
			"Succeeded",
			"Paid",
			{
				"amount_paid": 5710516,
				"hosted_invoice_url": "https://invoice.stripe.com/i/test",
				"status_transitions": {"paid_at": int(time.time())},
			},
		)

		self.assertIsNone(self._payment_processing_since())
		self.assertEqual(frappe.db.get_value("Invoice", self.invoice.name, "status"), "Paid")

	def test_payment_processing_older_than_14_days_is_cleared_by_daily_job(self):
		frappe.db.set_value(
			"Invoice", self.invoice.name, "payment_processing_since", add_days(now_datetime(), -15)
		)
		clear_stale_payment_processing()
		self.assertIsNone(self._payment_processing_since())

	def test_payment_processing_within_14_days_is_kept_by_daily_job(self):
		frappe.db.set_value(
			"Invoice", self.invoice.name, "payment_processing_since", add_days(now_datetime(), -13)
		)
		clear_stale_payment_processing()
		self.assertIsNotNone(self._payment_processing_since())

	def test_team_whose_only_unpaid_invoice_is_processing_is_not_suspended(self):
		plan = create_test_plan("Site", plan_name="Test Payment Processing Plan")
		create_test_site(team=self.team.name, plan=plan.name)
		self.assertIn(self.team.name, self._teams_to_suspend())

		self._receive_payment_processing_webhook()
		self.assertNotIn(self.team.name, self._teams_to_suspend())

	def _teams_to_suspend(self):
		return [row.team for row in get_teams_with_unpaid_invoices()]
