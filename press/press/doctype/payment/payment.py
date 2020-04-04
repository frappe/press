# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe.utils import nowdate
from datetime import datetime
from press.press.doctype.stripe_webhook_log.stripe_webhook_log import set_status


class Payment(Document):
	pass


def process_stripe_webhook(doc, method):
	"""This method runs after a Stripe Webhook Log is created"""
	if doc.event_type not in ["invoice.payment_succeeded", "invoice.payment_failed"]:
		return

	event = frappe.parse_json(doc.payload)
	invoice = event["data"]["object"]
	customer_id = invoice["customer"]
	# value is in cents or paise
	amount = invoice["total"] / 100

	team = frappe.db.get_value(
		"Team",
		{"stripe_customer_id": customer_id},
		["name", "transaction_currency"],
		as_dict=True,
	)
	if not team:
		team = frappe.db.get_value(
			"Team", "farisansari17@gmail.com", ["name", "transaction_currency"], as_dict=True
		)

	payment = frappe.get_doc(
		{
			"doctype": "Payment",
			"team": team.name,
			"amount": amount,
			"currency": team.transaction_currency,
			"stripe_invoice_id": invoice["id"],
			"payment_link": invoice["hosted_invoice_url"],
		}
	)

	if doc.event_type == "invoice.payment_succeeded":
		payment.payment_date = datetime.fromtimestamp(
			invoice["status_transitions"]["paid_at"]
		)
		payment.status = "Paid"
	elif doc.event_type == "invoice.payment_failed":
		payment.status = "Failed"

	payment.insert()
