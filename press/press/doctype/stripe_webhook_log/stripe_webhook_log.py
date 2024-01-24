# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

import press.utils
from press.api.billing import get_stripe
from frappe.model.document import Document
import re


class InvalidStripeWebhookEvent(Exception):
	http_status_code = 400


class StripeWebhookLog(Document):
	def before_insert(self):
		payload = frappe.parse_json(self.payload)
		self.name = payload.get("id")
		self.event_type = payload.get("type")
		customer_id = get_customer_id(payload)
		invoice_id = get_invoice_id(payload)
		if customer_id:
			self.customer_id = customer_id
			self.team = frappe.db.get_value("Team", {"stripe_customer_id": customer_id}, "name")

		if invoice_id:
			self.invoice_id = invoice_id
			self.invoice = frappe.db.get_value(
				"Invoice", {"stripe_invoice_id": invoice_id}, "name"
			)


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
		frappe.get_doc(
			doctype="Stripe Webhook Log",
			payload=frappe.as_json(event),
		).insert(ignore_if_duplicate=True)
	except Exception:
		frappe.db.rollback()
		press.utils.log_error(title="Stripe Webhook Handler", stripe_event_id=form_dict.id)
		frappe.set_user(current_user)
		raise Exception


def get_customer_id(form_dict):
	try:
		form_dict_str = frappe.as_json(form_dict)
		customer_id = re.search(r"cus_\w+", form_dict_str)
		if customer_id:
			return customer_id.group(0)
		else:
			return None
	except Exception:
		frappe.log_error(title="Failed to capture customer id from stripe webhook log")


def get_invoice_id(form_dict):
	try:
		form_dict_str = frappe.as_json(form_dict)
		invoice_id = re.search(r"in_\w+", form_dict_str)
		if invoice_id:
			return invoice_id.group(0)
		else:
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
