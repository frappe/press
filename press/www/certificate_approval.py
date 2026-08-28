# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.partner.doctype.certificate_link_request.certificate_link_request import (
	CertificateLinkRequest,
)

no_cache = 1


def get_context(context):
	"""Public consent page for a certificate holder to approve a partner's
	link request.

	The page is intentionally guest-accessible: the holder need not be a Frappe
	Cloud user. The GET renders the request for review (read-only); the POST,
	triggered by the holder clicking Approve, performs the approval. Keeping the
	mutation behind a POST prevents email scanners and link prefetchers (which
	issue GET requests) from approving on the holder's behalf.
	"""
	context.no_cache = 1

	key = frappe.form_dict.get("key")
	request = _get_request(key)

	if not request:
		context.state = "invalid"
		return context

	context.partner = request.partner or "A Frappe Cloud partner"
	context.course = _humanize_course(request.course)

	if frappe.request.method == "POST":
		if request.status != "Pending":
			context.state = "already_approved" if request.status == "Approved" else "invalid"
			return context
		try:
			CertificateLinkRequest.approve_from_key(key)
			frappe.db.commit()
			context.state = "approved"
		except frappe.ValidationError as e:
			frappe.db.rollback()
			context.state = "error"
			context.error_message = str(e)
		return context

	if request.status == "Pending":
		context.state = "pending"
	elif request.status == "Approved":
		context.state = "already_approved"
	else:
		context.state = "invalid"

	return context


def _get_request(key: str | None):
	if not key:
		return None
	name = frappe.db.get_value("Certificate Link Request", {"key": key}, "name")
	if not name:
		return None
	return frappe.db.get_value(
		"Certificate Link Request",
		name,
		["status", "partner", "course"],
		as_dict=True,
	)


def _humanize_course(course: str | None) -> str:
	if not course:
		return ""
	return course.replace("-", " ").title()
