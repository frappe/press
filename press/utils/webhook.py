# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe.model import default_fields
from frappe.model.document import Document


def create_webhook_event(event: str, payload: dict | Document, team: str) -> bool:
	try:
		# Check if team has configured webhook against this event
		PressWebhookSelectedEvent = frappe.qb.DocType("Press Webhook Selected Event")
		PressWebhook = frappe.qb.DocType("Press Webhook")

		query = (
			frappe.qb.from_(PressWebhookSelectedEvent)
			.select(frappe.query_builder.functions.Count(PressWebhookSelectedEvent.name).as_("count"))
			.left_join(PressWebhook)
			.on(PressWebhookSelectedEvent.parent == PressWebhook.name)
			.where(PressWebhookSelectedEvent.event == event)
			.where(PressWebhook.team == team)
			.where(PressWebhook.enabled == 1)
		)

		result = query.run(as_dict=True)
		is_any_webhook_enabled = result and result[0].get("count") > 0
		if is_any_webhook_enabled:
			# prepare request payload
			data = {}
			if isinstance(payload, dict):
				data = frappe._dict(payload)
			elif isinstance(payload, Document):
				data = _process_document_payload(payload)
			else:
				frappe.throw("Invalid data type")

			request_payload = json.dumps(
				{
					"event": event,
					"data": data,
				},
				default=str,
				indent=4,
			)

			# create webhook log
			frappe.get_doc(
				{
					"doctype": "Press Webhook Log",
					"status": "Pending",
					"event": event,
					"team": team,
					"request_payload": request_payload,
				}
			).insert(ignore_permissions=True)
		return True
	except Exception:
		frappe.log_error("failed to queue webhook event")
		return False


UNNECESSARY_FIELDS_OF_PAYLOAD = ("build_steps", "apps")


def _process_document_payload(payload: Document):
	# convert payload to dict
	# send fields mentioned in dashboard_fields, as other fields can have sensitive information
	fields = list(default_fields)
	if hasattr(payload, "dashboard_fields"):
		fields += payload.dashboard_fields

	fields = [field for field in fields if field not in UNNECESSARY_FIELDS_OF_PAYLOAD]

	_doc = frappe._dict()
	for fieldname in fields:
		_doc[fieldname] = payload.get(fieldname)

	return _doc
