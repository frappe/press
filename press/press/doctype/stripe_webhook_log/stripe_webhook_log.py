# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import re
from datetime import datetime

import frappe
from frappe.model.document import Document

import press.utils
from press.api.billing import get_stripe


class InvalidStripeWebhookEvent(Exception):
	http_status_code = 400


class StripeWebhookLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		customer_id: DF.Data | None
		event_type: DF.Data | None
		invoice: DF.Link | None
		invoice_id: DF.Data | None
		payload: DF.Code | None
		stripe_payment_intent_id: DF.Data | None
		stripe_payment_method: DF.Link | None
		team: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		payload = frappe.parse_json(self.payload)
		self.name = payload.get("id")
		self.event_type = payload.get("type")
		customer_id = get_customer_id(payload)
		invoice_id = get_invoice_id(payload)
		self.stripe_payment_intent_id = ""

		if self.event_type in [
			"payment_intent.succeeded",
			"payment_intent.failed",
			"payment_intent.requires_action",
		]:
			self.stripe_payment_intent_id = get_intent_id(payload)

		if customer_id:
			self.customer_id = customer_id
			self.team = frappe.db.get_value("Team", {"stripe_customer_id": customer_id}, "name")

		if invoice_id:
			self.invoice_id = invoice_id
			self.invoice = frappe.db.get_value("Invoice", {"stripe_invoice_id": invoice_id}, "name")

		if self.event_type == "payment_intent.payment_failed":
			payment_method = (
				payload.get("data", {}).get("object", {}).get("last_payment_error", {}).get("payment_method")
			)
			if payment_method:
				payment_method_id = payment_method.get("id")

				self.stripe_payment_method = frappe.db.get_value(
					"Stripe Payment Method",
					{"stripe_customer_id": customer_id, "stripe_payment_method_id": payment_method_id},
					"name",
				)

		if (
			self.event_type == "invoice.payment_failed"
			and self.invoice
			and payload.get("data", {}).get("object", {}).get("next_payment_attempt")
		):
			next_payment_attempt_date = datetime.fromtimestamp(
				payload.get("data", {}).get("object", {}).get("next_payment_attempt")
			).strftime("%Y-%m-%d")
			frappe.db.set_value(
				"Invoice",
				self.invoice,
				"next_payment_attempt_date",
				frappe.utils.getdate(next_payment_attempt_date),
			)


def allow_insert_log(event):
	if isinstance(event, str):
		event = frappe.parse_json(event)
	evt_id = event.get("id")
	invoice_id = get_invoice_id(event)
	intent_id = get_intent_id(event)

	description = None
	if event.get("type") == "payment_intent.succeeded":
		description = event["data"]["object"]["description"]

	if not frappe.db.exists("Stripe Webhook Log", evt_id):
		return True

	if invoice_id and frappe.db.get_value("Invoice", {"stripe_invoice_id": invoice_id}, "status") == "Paid":
		# Do not insert duplicate webhook logs for invoices that are already paid
		return False

	if (
		description
		and description == "Prepaid Credits"
		and intent_id
		and frappe.db.exists(
			"Invoice", {"type": "Prepaid Credits", "status": "Paid", "stripe_payment_intent_id": intent_id}
		)
	):
		return False

	frappe.delete_doc("Stripe Webhook Log", evt_id)
	return True


@frappe.whitelist(allow_guest=True)
def stripe_webhook_handler():
	current_user = frappe.session.user
	form_dict = frappe.local.form_dict
	try:
		payload = frappe.request.get_data()
		signature = frappe.get_request_header("Stripe-Signature")
		# parse payload will verify the request
		event = parse_payload(payload, signature)
		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		if not allow_insert_log(event):
			return
		frappe.get_doc(
			doctype="Stripe Webhook Log",
			payload=frappe.as_json(event),
		).insert()
	except Exception:
		frappe.db.rollback()
		press.utils.log_error(title="Stripe Webhook Handler", stripe_event_id=form_dict.id)
		frappe.set_user(current_user)
		raise


def get_intent_id(form_dict):
	try:
		form_dict_str = frappe.as_json(form_dict)
		intent_id = re.findall(r"pi_\w+", form_dict_str)
		if intent_id:
			return intent_id[1]
		return None
	except IndexError:
		return None
	except Exception:
		frappe.log_error(title="Failed to capture intent id from stripe webhook log")


def get_customer_id(form_dict):
	try:
		form_dict_str = frappe.as_json(form_dict)
		customer_id = re.search(r"cus_\w+", form_dict_str)
		if customer_id:
			return customer_id.group(0)
		return None
	except Exception:
		frappe.log_error(title="Failed to capture customer id from stripe webhook log")


def get_invoice_id(form_dict):
	try:
		form_dict_str = frappe.as_json(form_dict)
		invoice_id = re.search(r"in_\w+", form_dict_str)
		if invoice_id:
			return invoice_id.group(0)
		return None
	except Exception:
		frappe.log_error(title="Failed to capture invoice id from stripe webhook log")


def parse_payload(payload, signature):
	secret = frappe.db.get_single_value("Press Settings", "stripe_webhook_secret")
	stripe = get_stripe()
	try:
		return stripe.Webhook.construct_event(payload, signature, secret)
	except ValueError:
		# Invalid payload
		frappe.throw("Invalid Payload", InvalidStripeWebhookEvent)
	except stripe.error.SignatureVerificationError:
		# Invalid signature
		frappe.throw("Invalid Signature", InvalidStripeWebhookEvent)
