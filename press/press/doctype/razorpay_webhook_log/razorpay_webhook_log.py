# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

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
