# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import press.utils
from frappe.model.document import Document
from press.api.billing import get_stripe


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
			}
		).insert(ignore_if_duplicate=True)
	except Exception:
		frappe.db.rollback()
		press.utils.log_error(title="Stripe Webhook Handler", stripe_event_id=form_dict.id)
		frappe.set_user(current_user)
		raise Exception


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
