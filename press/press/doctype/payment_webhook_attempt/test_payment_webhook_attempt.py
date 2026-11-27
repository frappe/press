# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today

from press.press.doctype.payment_webhook_attempt.payment_webhook_attempt import (
	PaymentWebhookAttempt,
	WebhookAttemptRecorder,
)
from press.press.report.payment_webhook_delays.payment_webhook_delays import execute as run_report

RECORDER_MODULE = "press.press.doctype.payment_webhook_attempt.payment_webhook_attempt"


def unix_time(minutes_ago: int) -> int:
	return int((now_datetime() - timedelta(minutes=minutes_ago)).timestamp())


def record_attempt(order_id: str, minutes_late: int = 0, error: Exception | None = None) -> dict:
	recorder = WebhookAttemptRecorder("Razorpay")
	recorder.verified(
		event_id=frappe.generate_hash(length=14),
		event_type="order.paid",
		event_created_at=unix_time(minutes_late),
		order_id=order_id,
		payment_id=f"pay_{order_id}",
	)
	if error:
		recorder.failed(error)
	else:
		recorder.processed()
	return frappe.get_last_doc("Payment Webhook Attempt", {"order_id": order_id})


def report_rows(only_delayed: int = 1) -> list[dict]:
	_, rows = run_report({"from_date": today(), "to_date": today(), "only_delayed": only_delayed})
	return rows


@patch(f"{RECORDER_MODULE}.frappe.db.commit", new=MagicMock())
class TestPaymentWebhookAttempt(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_attempt_records_how_late_the_gateway_delivered_the_event(self):
		attempt = record_attempt("order_late", minutes_late=36)

		self.assertEqual(attempt.status, "Processed")
		self.assertAlmostEqual(attempt.delivery_delay, 36 * 60, delta=5)
		self.assertGreaterEqual(attempt.processing_time, 0)

	def test_failed_attempt_keeps_the_error_for_the_report(self):
		attempt = record_attempt("order_failed", error=frappe.ValidationError("Lock wait timeout"))

		self.assertEqual(attempt.status, "Failed")
		self.assertEqual(attempt.error, "ValidationError: Lock wait timeout")

	def test_failure_before_signature_check_records_nothing(self):
		WebhookAttemptRecorder("Razorpay").failed(ValueError("Invalid signature"))

		self.assertFalse(
			frappe.db.exists("Payment Webhook Attempt", {"error": ("like", "%Invalid signature%")})
		)

	def test_report_shows_late_and_failed_payments_but_hides_on_time_ones(self):
		record_attempt("order_on_time")
		record_attempt("order_late", minutes_late=10)
		record_attempt("order_retried", error=frappe.ValidationError("Lock wait timeout"))
		record_attempt("order_retried")

		rows = {(row.order_id, row.status): row for row in report_rows()}

		self.assertNotIn(("order_on_time", "Processed"), rows)
		self.assertIn(("order_late", "Processed"), rows)
		self.assertEqual(rows[("order_retried", "Processed")].failed_attempts, 1)

	def test_report_shows_every_attempt_when_delay_filter_is_off(self):
		record_attempt("order_on_time")

		self.assertIn("order_on_time", [row.order_id for row in report_rows(only_delayed=0)])

	def test_log_cleanup_deletes_attempts_older_than_ninety_days(self):
		old = record_attempt("order_old")
		recent = record_attempt("order_recent")
		frappe.db.set_value("Payment Webhook Attempt", old.name, "creation", add_days(now_datetime(), -91))

		PaymentWebhookAttempt.clear_old_logs()

		self.assertFalse(frappe.db.exists("Payment Webhook Attempt", old.name))
		self.assertTrue(frappe.db.exists("Payment Webhook Attempt", recent.name))
