# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from typing import List
import frappe


@frappe.whitelist(allow_guest=True)
def available_events():
	return frappe.get_all(
		"Press Webhook Event",
		fields=["name", "description"],
		filters={"enabled": 1},
		order_by="creation desc",
	)


@frappe.whitelist()
def add(endpoint: str, secret: str, events: List[str]):
	doc = frappe.new_doc("Press Webhook")
	doc.endpoint = endpoint
	doc.secret = secret
	doc.team = frappe.local.team().name
	for event in events:
		doc.append("events", {"event": event})
	doc.save()