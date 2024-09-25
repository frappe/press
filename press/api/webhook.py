# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

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


@frappe.whitelist()
def attempts(webhook: str, page_length: int = 20, offset: int = 0):
	doc = frappe.get_doc("Press Webhook", webhook)
	doc.has_permission("read")

	PressWebhookAttempt = frappe.qb.DocType("Press Webhook Attempt")
	PressWebhookLog = frappe.qb.DocType("Press Webhook Log")
	query = (
		frappe.qb.from_(PressWebhookAttempt)
		.select(
			PressWebhookAttempt.name,
			PressWebhookAttempt.endpoint,
			PressWebhookLog.event,
			PressWebhookAttempt.status,
			PressWebhookAttempt.response_status_code,
			PressWebhookAttempt.timestamp,
		)
		.left_join(PressWebhookLog)
		.on(PressWebhookAttempt.parent == PressWebhookLog.name)
		.where(PressWebhookAttempt.webhook == doc.name)
		.orderby(PressWebhookAttempt.timestamp, order=frappe.qb.desc)
		.offset(offset)
		.limit(page_length)
	)
	return query.run(as_dict=1)


@frappe.whitelist()
def attempt(name: str):
	doc = frappe.get_doc("Press Webhook Attempt", name)
	doc.has_permission("read")
	data = doc.as_dict()
	data.request_payload = json.loads(frappe.get_value("Press Webhook Log", doc.parent, "request_payload"))
	return data
