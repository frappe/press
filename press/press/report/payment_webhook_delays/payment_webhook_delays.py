# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from collections import Counter

import frappe
from frappe import _

DELAY_THRESHOLD_SECONDS = 60


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_data(filters) -> list[frappe._dict]:
	attempts = get_attempts(filters)
	failures = Counter(payment_key(row) for row in attempts if row.status == "Failed")
	for row in attempts:
		row.failed_attempts = failures[payment_key(row)]
	if filters.only_delayed:
		return [row for row in attempts if needs_attention(row)]
	return attempts


def get_attempts(filters) -> list[frappe._dict]:
	conditions = {"received_at": ("between", [filters.from_date, filters.to_date])}
	if filters.gateway:
		conditions["gateway"] = filters.gateway
	return frappe.get_all(
		"Payment Webhook Attempt",
		filters=conditions,
		fields=[
			"name",
			"gateway",
			"event_type",
			"order_id",
			"payment_id",
			"event_id",
			"event_created_at",
			"received_at",
			"log_created_at",
			"delivery_delay",
			"processing_time",
			"status",
			"webhook_log_type",
			"webhook_log",
			"error",
		],
		order_by="received_at desc",
	)


def payment_key(row) -> tuple:
	return (row.gateway, row.order_id or row.payment_id or row.event_id)


def needs_attention(row) -> bool:
	return (
		row.delivery_delay > DELAY_THRESHOLD_SECONDS
		or row.processing_time > DELAY_THRESHOLD_SECONDS
		or row.failed_attempts > 0
	)


def get_columns() -> list[dict]:
	return [
		{"label": _("Gateway"), "fieldname": "gateway", "fieldtype": "Data", "width": 90},
		{"label": _("Event Type"), "fieldname": "event_type", "fieldtype": "Data", "width": 160},
		{"label": _("Order / Invoice ID"), "fieldname": "order_id", "fieldtype": "Data", "width": 190},
		{"label": _("Payment ID"), "fieldname": "payment_id", "fieldtype": "Data", "width": 190},
		{"label": _("Event ID"), "fieldname": "event_id", "fieldtype": "Data", "width": 170},
		{
			"label": _("Webhook Triggered At"),
			"fieldname": "event_created_at",
			"fieldtype": "Datetime",
			"width": 165,
		},
		{"label": _("Received At"), "fieldname": "received_at", "fieldtype": "Datetime", "width": 165},
		{"label": _("Log Created At"), "fieldname": "log_created_at", "fieldtype": "Datetime", "width": 165},
		{"label": _("Delivery Delay"), "fieldname": "delivery_delay", "fieldtype": "Duration", "width": 120},
		{
			"label": _("Processing Time (s)"),
			"fieldname": "processing_time",
			"fieldtype": "Float",
			"width": 130,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Failed Attempts"), "fieldname": "failed_attempts", "fieldtype": "Int", "width": 120},
		{
			"label": _("Webhook Log"),
			"fieldname": "webhook_log",
			"fieldtype": "Dynamic Link",
			"options": "webhook_log_type",
			"width": 190,
		},
		{
			"label": _("Attempt"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Payment Webhook Attempt",
			"width": 110,
		},
		{"label": _("Error"), "fieldname": "error", "fieldtype": "Data", "width": 250},
	]
