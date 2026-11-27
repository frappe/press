# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import time
from datetime import datetime, timezone

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, convert_utc_to_system_timezone, now_datetime


class PaymentWebhookAttempt(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		delivery_delay: DF.Float
		error: DF.SmallText | None
		event_created_at: DF.Datetime | None
		event_id: DF.Data | None
		event_type: DF.Data | None
		gateway: DF.Literal["Razorpay", "Stripe"]
		log_created_at: DF.Datetime | None
		order_id: DF.Data | None
		payment_id: DF.Data | None
		processing_time: DF.Float
		received_at: DF.Datetime | None
		status: DF.Literal["Processed", "Duplicate", "Failed"]
		webhook_log: DF.DynamicLink | None
		webhook_log_type: DF.Link | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days: int = 90):
		frappe.db.delete("Payment Webhook Attempt", {"creation": ("<", add_days(now_datetime(), -days))})


class WebhookAttemptRecorder:
	"""Times one webhook request and records how it ended, once its signature is verified."""

	def __init__(self, gateway: str):
		self.gateway = gateway
		self.received_at = now_datetime()
		self.started = time.monotonic()
		self.event: dict | None = None

	def verified(
		self,
		event_id: str | None,
		event_type: str | None,
		event_created_at: int | None,
		order_id: str | None = None,
		payment_id: str | None = None,
	):
		self.event = {
			"event_id": event_id,
			"event_type": event_type,
			"event_created_at": from_unix_time(event_created_at),
			"order_id": order_id,
			"payment_id": payment_id,
		}

	def processed(self, log_doctype: str | None = None, log_name: str | None = None, duplicate=False):
		self.insert("Duplicate" if duplicate else "Processed", log_doctype, log_name)

	def failed(self, error: Exception):
		"""Keep the failed attempt, because the request rolls back everything else."""
		if not self.event:
			return
		self.insert("Failed", error=f"{type(error).__name__}: {error}"[:1000])
		frappe.db.commit()

	def insert(self, status, log_doctype=None, log_name=None, error=None):
		if not self.event:
			return
		frappe.get_doc(
			{
				"doctype": "Payment Webhook Attempt",
				"gateway": self.gateway,
				"status": status,
				**self.event,
				"received_at": self.received_at,
				"delivery_delay": delivery_delay(self.event["event_created_at"], self.received_at),
				"processing_time": round(time.monotonic() - self.started, 3),
				"webhook_log_type": log_doctype if log_name else None,
				"webhook_log": log_name,
				"log_created_at": log_name and frappe.db.get_value(log_doctype, log_name, "creation"),
				"error": error,
			}
		).insert(ignore_permissions=True)


def delivery_delay(event_created_at: datetime | None, received_at: datetime) -> float:
	if not event_created_at:
		return 0
	return max((received_at - event_created_at).total_seconds(), 0)


def from_unix_time(timestamp: int | None) -> datetime | None:
	if not timestamp:
		return None
	utc_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
	return convert_utc_to_system_timezone(utc_time).replace(tzinfo=None)
