# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import format_datetime
from frappe.utils.html_utils import sanitize_html

from press.press.doctype.support_access.support_access import SupportAccess

no_cache = 1

PERMISSION_FIELDS = (
	"login_as_administrator",
	"site_domains",
	"site_release_group",
	"bench_ssh",
	"server_ssh",
)
VALIDITY_OPTIONS = {
	"3": "3 hours",
	"6": "6 hours",
	"12": "12 hours",
	"24": "1 day",
	"72": "3 days",
	"168": "7 days",
}


def get_context(context):
	"""Public page where the team owner answers a support access request from the email.

	A GET only shows the request, so mail scanners that open links cannot answer it. The buttons POST.
	"""
	context.no_cache = 1
	form = frappe.form_dict
	access = SupportAccess.from_signed_params(form.request, form.team, form._signature)
	if not access:
		context.state = "invalid"
		return context

	if frappe.request.method == "POST" and access.status == "Pending":
		answer(access, context)

	context.state = context.state or access.status
	context.access = access
	context.signature = form._signature  # The Jinja sandbox hides names that start with _
	# Frappe stores the reason as sanitized HTML, so escaping it again would show &amp;
	context.reason = sanitize_html(access.reason or "")
	context.allowed_till = access_allowed_till(access)
	context.permissions = requested_permissions(access)
	context.validity_options = VALIDITY_OPTIONS
	return context


def answer(access: SupportAccess, context):
	try:
		access.answer_from_email(frappe.form_dict.answer, frappe.form_dict.allowed_for)
	except frappe.ValidationError as e:
		frappe.db.rollback()
		access.reload()
		context.state = "error"
		context.error_message = str(e)
	except Exception:
		# A web page POST commits even when the page fails, so undo a half-done answer
		frappe.db.rollback()
		raise


def access_allowed_till(access: SupportAccess) -> str:
	if not access.access_allowed_till:
		return ""
	return format_datetime(access.access_allowed_till, "d MMM yyyy, h:mm a")


def requested_permissions(access: SupportAccess) -> list[str]:
	meta = frappe.get_meta("Support Access")
	return [meta.get_label(field) for field in PERMISSION_FIELDS if access.get(field)]
