# Copyright (c) 2022, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from press.press.doctype.razorpay_webhook_log.razorpay_webhook_log import razorpay_webhook_handler
from press.press.doctype.team.test_team import create_test_team

HANDLER_MODULE = "press.press.doctype.razorpay_webhook_log.razorpay_webhook_log"


def order_paid_event(order_id: str, payment_id: str) -> frappe._dict:
	return frappe._dict(
		{
			"event": "order.paid",
			"created_at": int(now_datetime().timestamp()) - 120,
			"payload": {
				"payment": {"entity": {"id": payment_id, "order_id": order_id, "status": "captured"}}
			},
		}
	)


def deliver(event: frappe._dict, event_id: str):
	frappe.local.form_dict = event
	headers = {"X-Razorpay-Event-Id": event_id, "X-Razorpay-Signature": "signature"}
	with (
		patch(f"{HANDLER_MODULE}.frappe.request", new=MagicMock()),
		patch(f"{HANDLER_MODULE}.frappe.get_request_header", side_effect=headers.get),
	):
		razorpay_webhook_handler()


@patch(f"{HANDLER_MODULE}.get_razorpay_client", new=MagicMock())
class TestRazorpayWebhookLog(FrappeTestCase):
	def setUp(self):
		self.order_id = f"order_{frappe.generate_hash(length=14)}"
		self.payment_id = f"pay_{frappe.generate_hash(length=14)}"
		frappe.get_doc(
			{
				"doctype": "Razorpay Payment Record",
				"team": create_test_team().name,
				"order_id": self.order_id,
				"status": "Pending",
				"type": "Partnership Fee",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_retried_delivery_of_same_order_is_recorded_as_duplicate_attempt(self):
		event = order_paid_event(self.order_id, self.payment_id)

		deliver(event, "evt_first")
		deliver(event, "evt_retry")

		attempts = frappe.get_all(
			"Payment Webhook Attempt",
			{"order_id": self.order_id},
			["event_id", "status", "payment_id", "webhook_log", "log_created_at", "delivery_delay"],
			order_by="creation asc",
		)
		self.assertEqual(
			[(a.event_id, a.status) for a in attempts],
			[("evt_first", "Processed"), ("evt_retry", "Duplicate")],
		)
		self.assertEqual(attempts[0].payment_id, self.payment_id)
		self.assertEqual(attempts[0].webhook_log, self.order_id)
		self.assertIsNotNone(attempts[0].log_created_at)
		self.assertAlmostEqual(attempts[0].delivery_delay, 120, delta=5)
