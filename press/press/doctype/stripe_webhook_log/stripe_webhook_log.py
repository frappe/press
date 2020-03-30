# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document

class StripeWebhookLog(Document):
	pass

@frappe.whitelist(allow_guest=True)
def stripe_webhooks_logger():
	try:
		data = frappe.local.form_dict

		doc = frappe.get_doc({
			"data": json.dumps(frappe.local.form_dict),
			"doctype": "Stripe Webhook Log",
			"status": "Queued",
			"event_type": data.get("type")
		}).insert(ignore_permissions=True)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error()

def set_status(name, status):
	frappe.db.set_value("Stripe Webhook Log", name, "status", status)
	frappe.db.commit()
