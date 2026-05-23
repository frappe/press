# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import hashlib
import hmac
import json

import frappe
from frappe.model.document import Document

import press.utils


class ChargilyWebhookLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency | None
		checkout_id: DF.Data | None
		event_type: DF.Data | None
		invoice: DF.Link | None
		payload: DF.Code | None
		payment_method: DF.Data | None
		status: DF.Data | None
		team: DF.Link | None
	# end: auto-generated types

	pass


class InvalidChargilyWebhookEvent(Exception):
	http_status_code = 400


@frappe.whitelist(allow_guest=True)
def chargily_webhook_handler():
	current_user = frappe.session.user
	try:
		payload = frappe.request.get_data(as_text=True)
		signature = frappe.request.headers.get("signature", "")

		from frappe.utils.password import get_decrypted_password
		secret = get_decrypted_password("Press Settings", "Press Settings", "chargily_webhook_secret", raise_exception=False)
		if not secret:
			secret = get_decrypted_password("Press Settings", "Press Settings", "chargily_api_secret", raise_exception=False)
		if not secret:
			frappe.throw("Chargily Webhook Secret not configured", InvalidChargilyWebhookEvent)

		# Verify HMAC-SHA256 signature
		expected = hmac.new(
			secret.encode("utf-8"),
			payload.encode("utf-8"),
			hashlib.sha256,
		).hexdigest()

		if not hmac.compare_digest(expected, signature):
			frappe.throw("Invalid webhook signature", frappe.AuthenticationError)

		event = json.loads(payload)
		event_type = event.get("type", "")
		checkout_data = event.get("data", {})

		# Extract metadata to find invoice and team
		metadata = checkout_data.get("metadata", [])
		invoice_name = None
		team_name = None
		for m in metadata:
			if m.get("key") == "invoice":
				invoice_name = m.get("value")
			if m.get("key") == "team":
				team_name = m.get("value")

		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		# Create webhook log
		log = frappe.get_doc(
			{
				"doctype": "Chargily Webhook Log",
				"event_type": event_type,
				"payload": payload,
				"checkout_id": checkout_data.get("id"),
				"invoice": invoice_name,
				"team": team_name,
				"payment_method": checkout_data.get("payment_method"),
				"amount": checkout_data.get("amount"),
				"status": checkout_data.get("status"),
			}
		)
		log.insert(ignore_permissions=True)
		frappe.db.commit()

		# Process the event
		if event_type == "checkout.paid" and invoice_name:
			_handle_checkout_paid(invoice_name, checkout_data)
		elif event_type == "checkout.paid" and team_name and not invoice_name:
			_handle_prepaid_credits(team_name, checkout_data)

	except Exception:
		frappe.db.rollback()
		press.utils.log_error(title="Chargily Webhook Handler")
		frappe.set_user(current_user)
		raise

	return {"status": "ok"}


def _handle_checkout_paid(invoice_name, checkout_data):
	"""Handle a successful checkout payment for an invoice."""
	try:
		invoice = frappe.get_doc("Invoice", invoice_name)
		if invoice.status != "Paid":
			invoice.status = "Paid"
			invoice.amount_paid = invoice.total
			invoice.save(ignore_permissions=True)
			invoice.submit()
			frappe.db.commit()
	except Exception:
		frappe.log_error("Chargily Webhook: Error processing checkout.paid for invoice")


def _handle_prepaid_credits(team_name, checkout_data):
	"""Handle a successful checkout payment for prepaid credits (no invoice)."""
	try:
		amount = checkout_data.get("amount", 0)
		if amount <= 0:
			return

		balance_transaction = frappe.get_doc(
			doctype="Balance Transaction",
			team=team_name,
			source="Prepaid Credits",
			type="Adjustment",
			amount=amount,
			description="Chargily Pay - Prepaid Credits",
		)
		balance_transaction.insert(ignore_permissions=True)
		balance_transaction.submit()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team_name,
			type="Prepaid Credits",
			status="Paid",
			total=amount,
			amount_due=amount,
			amount_paid=amount,
			amount_due_with_tax=amount,
			due_date=frappe.utils.nowdate(),
		)
		invoice.append(
			"items",
			{
				"description": "Prepaid Credits",
				"document_type": "Balance Transaction",
				"document_name": balance_transaction.name,
				"quantity": 1,
				"rate": amount,
			},
		)
		invoice.insert(ignore_permissions=True)
		invoice.submit()
		frappe.db.commit()
	except Exception:
		frappe.log_error("Chargily Webhook: Error processing prepaid credits")
