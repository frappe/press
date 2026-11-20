# Copyright (c) 2022, Frappe and Contributors
# See license.txt
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.razorpay_payment_record.razorpay_payment_record import (
	RazorpayPaymentRecord,
	fetch_recent_pending_payment_orders,
)
from press.press.doctype.team.test_team import create_test_team

PAYMENT_AMOUNT_IN_PAISE = 118000  # ₹1,000 + ₹180 GST


def create_pending_payment_record(team: str, order_id: str) -> RazorpayPaymentRecord:
	return frappe.get_doc(
		{
			"doctype": "Razorpay Payment Record",
			"team": team,
			"order_id": order_id,
			"status": "Pending",
			"type": "Prepaid Credits",
		}
	).insert(ignore_permissions=True)


def captured_payment(payment_id: str, order_id: str) -> dict:
	return {
		"id": payment_id,
		"order_id": order_id,
		"status": "captured",
		"amount": PAYMENT_AMOUNT_IN_PAISE,
		"currency": "INR",
		"method": "upi",
		"notes": {"gst": 180},
		"fee": 0,
		"tax": 0,
		"created_at": int(datetime.now().timestamp()),
	}


def mock_razorpay_client(payment: dict) -> MagicMock:
	client = MagicMock()
	client.payment.fetch.return_value = payment
	client.order.payments.return_value = {"items": [payment]}
	return client


def deliver_order_paid_webhook(order_id: str, payment_id: str):
	frappe.get_doc(
		{
			"doctype": "Razorpay Webhook Log",
			"name": order_id,
			"event": "order.paid",
			"payment_id": payment_id,
			"payload": "{}",
		}
	).insert(ignore_if_duplicate=True)


@patch(
	"press.press.doctype.razorpay_payment_record.razorpay_payment_record.frappe.db.commit", new=MagicMock()
)
class TestRazorpayPaymentRecord(FrappeTestCase):
	def setUp(self):
		self.team = create_test_team()
		self.order_id = f"order_{frappe.generate_hash(length=14)}"
		self.payment_id = f"pay_{frappe.generate_hash(length=14)}"
		self.client = mock_razorpay_client(captured_payment(self.payment_id, self.order_id))
		patcher = patch(
			"press.press.doctype.razorpay_payment_record.razorpay_payment_record.get_razorpay_client",
			return_value=self.client,
		)
		patcher.start()
		self.addCleanup(patcher.stop)

	def tearDown(self):
		frappe.db.rollback()

	def prepaid_credit_invoices(self) -> list[str]:
		return frappe.get_all(
			"Invoice", {"team": self.team.name, "type": "Prepaid Credits", "docstatus": 1}, pluck="name"
		)

	def test_checkout_callback_marks_record_captured_and_credits_team_once(self):
		record = create_pending_payment_record(self.team.name, self.order_id)

		record.mark_captured(self.payment_id, "signature")

		record.reload()
		self.assertEqual(record.status, "Captured")
		self.assertEqual(record.signature, "signature")
		self.assertEqual(len(self.prepaid_credit_invoices()), 1)

	def test_late_webhook_does_not_credit_again_after_checkout_callback_credited_the_team(self):
		record = create_pending_payment_record(self.team.name, self.order_id)
		record.mark_captured(self.payment_id, "signature")

		deliver_order_paid_webhook(self.order_id, self.payment_id)

		self.assertEqual(len(self.prepaid_credit_invoices()), 1)
		self.assertEqual(self.client.payment.fetch.call_count, 1)

	def test_webhook_credits_team_when_checkout_callback_never_arrived(self):
		create_pending_payment_record(self.team.name, self.order_id)

		deliver_order_paid_webhook(self.order_id, self.payment_id)

		record_status = frappe.db.get_value("Razorpay Payment Record", {"order_id": self.order_id}, "status")
		self.assertEqual(record_status, "Captured")
		self.assertEqual(len(self.prepaid_credit_invoices()), 1)

	def test_recent_pending_order_sync_credits_team_while_webhook_is_delayed(self):
		create_pending_payment_record(self.team.name, self.order_id)

		fetch_recent_pending_payment_orders()

		record_status = frappe.db.get_value("Razorpay Payment Record", {"order_id": self.order_id}, "status")
		self.assertEqual(record_status, "Captured")
		self.assertEqual(len(self.prepaid_credit_invoices()), 1)
		self.client.order.payments.assert_called_once_with(self.order_id)

	def test_recent_pending_order_sync_skips_orders_older_than_two_hours(self):
		record = create_pending_payment_record(self.team.name, self.order_id)
		three_hours_ago = datetime.now() - timedelta(hours=3)
		frappe.db.set_value("Razorpay Payment Record", record.name, "creation", three_hours_ago)

		fetch_recent_pending_payment_orders()

		self.client.order.payments.assert_not_called()
		self.assertEqual(frappe.db.get_value("Razorpay Payment Record", record.name, "status"), "Pending")
