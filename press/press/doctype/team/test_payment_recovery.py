# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""A customer with suspended sites pays, and the sites come back."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.razorpay_webhook_log.razorpay_webhook_log import (
	_handle_recurring_payment_captured,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.team import Team, enqueue_finalize_unpaid_for_team, process_stripe_webhook
from press.press.doctype.team.test_team import create_test_team

STRIPE_FIXTURE = Path(__file__).parents[1] / "invoice/fixtures/stripe_payment_intent_succeeded_webhook.json"
STRIPE_CUSTOMER = "cus_H3L4w6RXJPKLQs"
STRIPE_INTENT = "pi_1HtDybGjnxV0XKmrq0F7ktU2"  # pragma: allowlist secret
CREDITS_IN_FIXTURE = 755.64


def stripe_payment_succeeded_event():
	return frappe._dict(event_type="payment_intent.succeeded", payload=STRIPE_FIXTURE.read_text())


def razorpay_payment_captured_payload(invoice: str):
	entity = {"id": "pay_test_recovery", "notes": {"invoice": invoice}, "fee": 0, "tax": 0}
	return {"event": "payment.captured", "payload": {"payment": {"entity": entity}}}


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
@patch.object(Invoice, "update_transaction_details", new=Mock())
@patch.object(Invoice, "update_razorpay_transaction_details", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
# The webhook handlers commit, which would leak records past the rollback
@patch("press.press.doctype.razorpay_webhook_log.razorpay_webhook_log.frappe.db.commit", new=Mock())
class TestPaymentRecovery(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.team.db_set({"payment_mode": "Prepaid Credits", "stripe_customer_id": STRIPE_CUSTOMER})
		self.site = create_test_site(team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()

	def create_unpaid_invoice(self, amount: float, days_ago: int = 40) -> Invoice:
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=add_days(today(), -days_ago),
			period_end=add_days(today(), -days_ago + 9),
		)
		invoice.append("items", {"quantity": 1, "rate": amount, "amount": amount})
		invoice.insert()
		invoice.finalize_invoice()
		invoice.reload()
		self.assertEqual(invoice.status, "Unpaid")
		return invoice

	def suspend_sites(self):
		Team("Team", self.team.name).suspend_sites(reason="Unpaid Invoices")
		self.assertEqual(self.site_status(), "Suspended")

	def site_status(self) -> str:
		return frappe.db.get_value("Site", self.site.name, "status")

	def pay_with_stripe(self):
		process_stripe_webhook(stripe_payment_succeeded_event(), "")
		enqueue_finalize_unpaid_for_team(self.team.name)

	def test_stripe_payment_adds_credits_and_records_a_paid_prepaid_credits_invoice(self):
		process_stripe_webhook(stripe_payment_succeeded_event(), "")

		self.assertEqual(Team("Team", self.team.name).get_balance(), CREDITS_IN_FIXTURE)
		invoice = frappe.get_value(
			"Invoice", {"stripe_payment_intent_id": STRIPE_INTENT}, ["type", "status"], as_dict=True
		)
		self.assertEqual((invoice.type, invoice.status), ("Prepaid Credits", "Paid"))

	def test_stripe_payment_delivered_twice_adds_credits_only_once(self):
		process_stripe_webhook(stripe_payment_succeeded_event(), "")
		process_stripe_webhook(stripe_payment_succeeded_event(), "")

		self.assertEqual(Team("Team", self.team.name).get_balance(), CREDITS_IN_FIXTURE)
		self.assertEqual(frappe.db.count("Invoice", {"stripe_payment_intent_id": STRIPE_INTENT}), 1)

	def test_stripe_payment_pays_the_unpaid_invoice_and_unsuspends_the_sites(self):
		invoice = self.create_unpaid_invoice(500)
		self.suspend_sites()

		self.pay_with_stripe()

		self.assertEqual(frappe.db.get_value("Invoice", invoice.name, "status"), "Paid")
		self.assertEqual(self.site_status(), "Active")

	def test_sites_stay_suspended_while_another_invoice_is_still_unpaid(self):
		self.create_unpaid_invoice(500, days_ago=70)
		self.create_unpaid_invoice(500, days_ago=40)
		self.suspend_sites()

		self.pay_with_stripe()

		statuses = frappe.get_all(
			"Invoice",
			{"team": self.team.name, "type": "Subscription", "status": ("!=", "Draft")},
			pluck="status",
		)
		self.assertCountEqual(statuses, ["Paid", "Unpaid"])
		self.assertEqual(self.site_status(), "Suspended")

	def test_upi_autopay_payment_pays_the_unpaid_invoice_and_unsuspends_the_sites(self):
		invoice = self.create_unpaid_invoice(500)
		self.suspend_sites()

		_handle_recurring_payment_captured(razorpay_payment_captured_payload(invoice.name))

		invoice.reload()
		self.assertEqual((invoice.status, invoice.docstatus), ("Paid", 1))
		self.assertEqual(self.site_status(), "Active")

	def test_upi_autopay_payment_delivered_twice_is_ignored_the_second_time(self):
		invoice = self.create_unpaid_invoice(500)
		_handle_recurring_payment_captured(razorpay_payment_captured_payload(invoice.name))
		self.suspend_sites()

		_handle_recurring_payment_captured(razorpay_payment_captured_payload(invoice.name))

		self.assertEqual(self.site_status(), "Suspended")
