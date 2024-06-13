# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	logs = frappe.get_all(
		"Stripe Webhook Log",
		{"event_type": "payment_intent.payment_failed"},
		["name", "payload", "customer_id"],
	)

	for log in logs:
		payload = frappe.parse_json(log.payload)
		if payment_method_id := (
			payload.get("data", {})
			.get("object", {})
			.get("last_payment_error", {})
			.get("payment_method", {})
			.get("id")
		):
			stripe_payment_method = frappe.db.get_value(
				"Stripe Payment Method",
				{
					"stripe_customer_id": log.customer_id,
					"stripe_payment_method_id": payment_method_id,
				},
				"name",
			)
			frappe.db.set_value(
				"Stripe Webhook Log",
				log.name,
				"stripe_payment_method",
				stripe_payment_method,
				update_modified=False,
			)
