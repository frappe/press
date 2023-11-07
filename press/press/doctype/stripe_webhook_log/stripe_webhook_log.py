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
	pass


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
			{
				"doctype": "Stripe Webhook Log",
				"name": event.id,
				"payload": frappe.as_json(form_dict),
				"event_type": event.type,
				"customer_id": get_customer_id(form_dict),
			}
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
