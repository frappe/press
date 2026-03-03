# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json

import frappe
from frappe.model.document import Document

from press.utils import log_error
from press.utils.billing import get_razorpay_client


class RazorpayWebhookLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event: DF.Data | None
		payload: DF.Code | None
		payment_id: DF.Data | None
	# end: auto-generated types

	def after_insert(self):
		payment_record = frappe.get_doc("Razorpay Payment Record", {"order_id": self.name})

		if self.event in ("order.paid", "payment.captured") and payment_record.status != "Captured":
			payment_record.update({"payment_id": self.payment_id, "status": "Captured"})
			payment_record.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def razorpay_authorized_payment_handler():
	client = get_razorpay_client()
	form_dict = frappe.local.form_dict

	payment_id = None
	try:
		payload = frappe.request.get_data()
		signature = frappe.get_request_header("X-Razorpay-Signature")
		webhook_secret = frappe.db.get_single_value("Press Settings", "razorpay_webhook_secret")
		entity_data = form_dict["payload"]["payment"]["entity"]

		client.utility.verify_webhook_signature(payload.decode(), signature, webhook_secret)
		if entity_data["status"] != "authorized":
			raise Exception("invalid payment status received")
		payment_id = entity_data.get("id")
		order_id = entity_data.get("order_id", "")
		amount = entity_data.get("amount")
		notes = entity_data.get("notes")

		if not order_id:
			return

		razorpay_payment_record = frappe.db.exists("Razorpay Payment Record", {"order_id": order_id})
		if not razorpay_payment_record:
			# Don't log error if its not FrappeCloud order
			# Example of valid notes
			# "notes": {
			# 	"Description": "Order for Frappe Cloud Prepaid Credits",
			# 	"Team (Frappe Cloud ID)": "test@example.com"
			#   "gst": 245
			# },

			if notes and notes.get("description"):
				log_error(
					"Razorpay payment record for given order does not exist",
					order_id=order_id,
				)
			return

		# Only capture payment, if the status of order id is pending
		if frappe.db.get_value("Razorpay Payment Record", razorpay_payment_record, "status") != "Pending":
			return

		# Capture the authorized payment
		client.payment.capture(payment_id, amount)
	except Exception as e:
		error_message = str(e)
		if (
			"payment has already been captured" in error_message
			or "the order is already paid" in error_message
			or "id provided does not exist" in error_message
		):
			return
		log_error(
			title="Razorpay Authorized Payment Webhook Handler",
			payment_id=payment_id,
		)
		raise Exception from e


@frappe.whitelist(allow_guest=True)
def razorpay_webhook_handler():
	client = get_razorpay_client()
	current_user = frappe.session.user
	form_dict = frappe.local.form_dict

	try:
		payload = frappe.request.get_data()
		signature = frappe.get_request_header("X-Razorpay-Signature")
		webhook_secret = frappe.db.get_single_value("Press Settings", "razorpay_webhook_secret")

		client.utility.verify_webhook_signature(payload.decode(), signature, webhook_secret)

		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		entity_data = form_dict["payload"]["payment"]["entity"]
		razorpay_order_id = entity_data.get("order_id")

		if not razorpay_order_id:
			return

		razorpay_payment_record = frappe.db.exists("Razorpay Payment Record", {"order_id": razorpay_order_id})

		notes = form_dict["payload"]["payment"]["entity"]["notes"]
		if not razorpay_payment_record:
			# Don't log error if its not FrappeCloud order
			# Example of valid notes
			# "notes": {
			# 	"Description": "Order for Frappe Cloud Prepaid Credits",
			# 	"Team (Frappe Cloud ID)": "test@example.com",
			# 	"gst": 245
			# },

			if notes and notes.get("description"):
				log_error(
					"Razorpay payment record for given order does not exist",
					order_id=razorpay_order_id,
				)
			return

		frappe.get_doc(
			{
				"doctype": "Razorpay Webhook Log",
				"payload": frappe.as_json(form_dict),
				"event": form_dict.get("event"),
				"payment_id": form_dict["payload"]["payment"]["entity"]["id"],
				"name": razorpay_order_id,
			}
		).insert(ignore_if_duplicate=True)

	except Exception as e:
		frappe.db.rollback()
		log_error(
			title="Razorpay Webhook Handler",
			payment_id=form_dict["payload"]["payment"]["entity"]["id"],
		)
		frappe.set_user(current_user)
		raise Exception from e


@frappe.whitelist(allow_guest=True)
def razorpay_emandate_webhook_handler():
	"""
	Webhook handler for Razorpay eMandate events.

	Handles the following events:
	- token.confirmed: Mandate is activated after user authorization
	- payment.captured: Recurring payment was successful
	- payment.failed: Recurring payment failed
	"""
	client = get_razorpay_client()
	current_user = frappe.session.user
	form_dict = frappe.local.form_dict

	try:
		payload = frappe.request.get_data()
		signature = frappe.get_request_header("X-Razorpay-Signature")
		webhook_secret = frappe.db.get_single_value("Press Settings", "razorpay_webhook_secret")

		client.utility.verify_webhook_signature(payload.decode(), signature, webhook_secret)

		# set user to Administrator
		frappe.set_user("Administrator")

		event = form_dict.get("event")

		if event == "token.confirmed":
			_handle_token_confirmed(form_dict)
		elif event == "payment.captured":
			_handle_recurring_payment_captured(form_dict)
		elif event == "payment.failed":
			_handle_recurring_payment_failed(form_dict)

	except Exception as e:
		frappe.db.rollback()
		log_error(
			title="Razorpay eMandate Webhook Handler",
			event=form_dict.get("event"),
			payload=json.dumps(form_dict),
		)
		frappe.set_user(current_user)
		raise Exception from e
	finally:
		frappe.set_user(current_user)


def _handle_token_confirmed(form_dict):
	"""Handle token.confirmed event - mandate has been activated"""
	token_entity = form_dict.get("payload", {}).get("token", {}).get("entity", {})

	token_id = token_entity.get("id")
	customer_id = token_entity.get("customer_id")
	recurring_status = token_entity.get("recurring_details", {}).get("status")

	if recurring_status != "confirmed":
		return

	# Find the mandate by customer_id that's pending
	# The invoice_id in subscription_registration corresponds to our mandate_id
	notes = token_entity.get("notes", {})
	mandate_id = notes.get("mandate_id") if notes else None

	if mandate_id:
		# Find by mandate_id stored in notes
		mandate = frappe.db.get_value(
			"Razorpay Mandate",
			{"mandate_id": mandate_id, "status": "Pending"},
			"name",
		)
	else:
		# Fallback: find by customer_id
		mandate = frappe.db.get_value(
			"Razorpay Mandate",
			{"razorpay_customer_id": customer_id, "status": "Pending"},
			"name",
		)

	if not mandate:
		log_error(
			"Razorpay Mandate not found for token.confirmed event",
			customer_id=customer_id,
			token_id=token_id,
		)
		return

	# Activate the mandate
	mandate_doc = frappe.get_doc("Razorpay Mandate", mandate)
	umn = token_entity.get("recurring_details", {}).get("failure_reason")  # UMN is sometimes here
	upi_vpa = token_entity.get("vpa")

	# Get max_amount from token if available
	max_amount = token_entity.get("max_amount")
	if max_amount:
		mandate_doc.max_amount = max_amount / 100  # Convert from paise

	mandate_doc.activate(token_id, umn, upi_vpa)

	frappe.db.commit()


def _handle_recurring_payment_captured(form_dict):
	"""Handle payment.captured event for recurring payments"""
	payment_entity = form_dict.get("payload", {}).get("payment", {}).get("entity", {})

	payment_id = payment_entity.get("id")
	notes = payment_entity.get("notes", {})

	# Check if this is a recurring payment (has invoice note)
	invoice_name = notes.get("invoice") if notes else None
	if not invoice_name:
		return

	# Check if the invoice exists
	if not frappe.db.exists("Invoice", invoice_name):
		log_error(
			"Invoice not found for recurring payment",
			payment_id=payment_id,
			invoice_name=invoice_name,
		)
		return

	invoice = frappe.get_doc("Invoice", invoice_name)

	# Update invoice with payment details
	invoice.razorpay_payment_id = payment_id
	invoice.status = "Paid"
	invoice.amount_paid = invoice.amount_due_with_tax
	invoice.payment_date = frappe.utils.today()

	# Update transaction details
	invoice.update_razorpay_transaction_details(payment_entity)

	invoice.save(ignore_permissions=True)

	if invoice.docstatus == 0:
		invoice.submit()
		invoice.unsuspend_sites_if_applicable()

	frappe.db.commit()


def _handle_recurring_payment_failed(form_dict):
	"""Handle payment.failed event for recurring payments"""
	payment_entity = form_dict.get("payload", {}).get("payment", {}).get("entity", {})

	payment_id = payment_entity.get("id")
	notes = payment_entity.get("notes", {})
	error_description = payment_entity.get("error_description", "Payment failed")

	# Check if this is a recurring payment (has invoice note)
	invoice_name = notes.get("invoice") if notes else None
	if not invoice_name:
		return

	# Check if the invoice exists
	if not frappe.db.exists("Invoice", invoice_name):
		return

	invoice = frappe.get_doc("Invoice", invoice_name)
	invoice.add_comment(
		"Comment",
		f"Razorpay recurring payment failed: {error_description}. Payment ID: {payment_id}",
	)

	# Increment payment attempt count
	invoice.payment_attempt_count = (invoice.payment_attempt_count or 0) + 1
	invoice.payment_attempt_date = frappe.utils.today()
	invoice.save(ignore_permissions=True)

	frappe.db.commit()
