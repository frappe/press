# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.utils import format_datetime, now_datetime

from press.press.doctype.team_change.team_change import DOCUMENT_LABELS, TeamChange
from press.utils import get_current_team

if TYPE_CHECKING:
	from frappe.model.document import Document


def open_requests(doctype: str, name: str) -> list[dict]:
	"""Requests for this document that the receiving team can still accept, newest first."""
	return frappe.get_all(
		"Team Change",
		filters={"document_type": doctype, "document_name": name, "transfer_completed": 0, "cancelled": 0},
		# Requests made before expiry existed have no date and stay valid
		or_filters=[["expires_on", ">", now_datetime()], ["expires_on", "is", "not set"]],
		fields=["name", "to_team", "expires_on"],
		order_by="creation desc",
	)


def transfer_action(doc: Document, transfer_row: dict) -> dict:
	"""The Transfer row of the Actions tab, or a row to cancel the request already sent."""
	requests = open_requests(doc.doctype, doc.name)
	if not requests:
		return transfer_row

	latest = requests[0]
	to_email = frappe.db.get_value("Team", latest["to_team"], "user")
	waiting = f"Waiting for {to_email} to accept."
	if expires_on := latest["expires_on"]:
		waiting += f" The link expires on {format_datetime(expires_on, 'd MMM yyyy, h:mm a')}."
	return {
		**transfer_row,
		"action": "Cancel transfer request",
		"description": waiting,
		"button_label": "Cancel request",
		"doc_method": "cancel_change_team_request",
	}


def cancel_transfer_requests(doc: Document):
	"""Cancel every open request for `doc`, so none of the sent links work any more."""
	label = DOCUMENT_LABELS[doc.doctype]
	# Read from the database: a transfer accepted since `doc` was loaded has changed it
	if frappe.db.get_value(doc.doctype, doc.name, "team") != get_current_team():
		frappe.throw(
			f"This {label} doesn't belong to your current team. If the transfer was already accepted, "
			"it now belongs to the receiving team. Otherwise, switch to the owning team and try again."
		)

	# Nothing open (a double click, or it expired): there is nothing left to stop
	for request in open_requests(doc.doctype, doc.name):
		# Locked, so the receiver can't accept between the check and the save
		TeamChange("Team Change", request["name"], for_update=True).cancel()
