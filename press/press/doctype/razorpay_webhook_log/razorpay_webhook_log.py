# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.utils import log_error
from frappe.model.document import Document
from press.utils.billing import get_razorpay_client


class RazorpayWebhookLog(Document):
	def after_insert(self):
		payment_record = frappe.get_doc("Razorpay Payment Record", {"order_id": self.name})

		if (
			self.event in ("order.paid", "payment.captured")
			and payment_record.status != "Captured"
		):
			payment_record.update({"payment_id": self.payment_id, "status": "Captured"})
			payment_record.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def razorpay_webhook_handler():
	client = get_razorpay_client()
	current_user = frappe.session.user
	form_dict = frappe.local.form_dict

	try:
		payload = frappe.request.get_data()
		signature = frappe.get_request_header("X-Razorpay-Signature")
		webhook_secret = frappe.db.get_single_value(
			"Press Settings", "razorpay_webhook_secret"
		)

		client.utility.verify_webhook_signature(payload.decode(), signature, webhook_secret)

		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		razorpay_order_id = form_dict["payload"]["payment"]["entity"]["order_id"]
		if not frappe.db.exists(
			"Razorpay Payment Record",
			{"order_id": razorpay_order_id},
		):
			log_error(
				"Razorpay payment record for given order does not exist", order_id=razorpay_order_id
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

	except Exception:
		frappe.db.rollback()
		log_error(
			title="Razorpay Webhook Handler",
			payment_id=form_dict["payload"]["payment"]["entity"]["id"],
		)
		frappe.set_user(current_user)
		raise Exception
