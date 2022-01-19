# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document


class RazorpayWebhookLog(Document):
	pass


@frappe.whitelist(allow_guest=True)
def razorpay_webhook_handler():
	pass