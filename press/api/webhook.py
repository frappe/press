# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

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
def add(endpoint: str, secret: str, events: list[str]):
	doc = frappe.new_doc("Press Webhook")
	doc.endpoint = endpoint
	doc.secret = secret
	doc.team = frappe.local.team().name
	for event in events:
		doc.append("events", {"event": event})
	doc.save()


@frappe.whitelist()
def update(name: str, endpoint: str, secret: str, events: list[str]):
	doc = frappe.get_doc("Press Webhook", name)
	doc.endpoint = endpoint
	if secret:
		doc.secret = secret
	# reset event list
	doc.events = []
	# add new events
	for event in events:
		doc.append("events", {"event": event})
	doc.save()
