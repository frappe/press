import re

import frappe
from frappe import _
from frappe.model.base_document import get_controller
from frappe.permissions import get_valid_perms

from press.utils.user import is_desk_user

DOCUMENT_METHODS = {"run_doc_method", "frappe.handler.run_doc_method", "frappe.api.v2.run_doc_method"}
DOCUMENT_KEYS = ("docs", "document")
DASHBOARD_METHODS = {
	"press.api.client.run_doc_method": ("dt", None),
	"press.api.client.delete": ("doctype", "delete"),
}
READ_ONLY_ROLES = {"Press Support"}
METHOD_PATH = re.compile(r"^/api/(?:v1/|v2/)?method/(.+?)/?$")
RESOURCE_PATH = re.compile(r"^/api/(?:v1/)?resource/([^/]+)/.+$")
DOCUMENT_PATH = re.compile(r"^/api/v2/document/([^/]+)/.+/method/([^/]+)/?$")


def needs_staff_role(*roles: str):
	"""Mark a whitelisted document method that desk staff can call only with one of `roles`.

	Frappe runs a whitelisted document method for any user who can read the
	record, so a read-only staff role could otherwise press every button.
	"""

	def mark(method):
		method.staff_roles = roles
		return method

	return mark


def safe_for_readers(method):
	"""Mark a whitelisted document method that only reads, so read-only staff can call it."""
	method.is_safe_for_readers = True
	return method


def is_staff() -> bool:
	return frappe.session.user != "Administrator" and is_desk_user()


def get_request_path() -> str | None:
	request = getattr(frappe.local, "request", None)
	return request.path if request else None


def get_requested_method() -> str | None:
	"""The method an RPC request runs. Frappe runs `cmd` before it routes on the path."""
	if frappe.local.form_dict.get("cmd"):
		return frappe.local.form_dict.cmd
	match = METHOD_PATH.match(get_request_path() or "")
	return match.group(1) if match else None


def is_document_method_call() -> bool:
	method = get_requested_method()
	return bool(method) and frappe.override_whitelisted_method(method) in DOCUMENT_METHODS


def parse_sent_document(sent) -> dict:
	document = frappe.parse_json(sent)
	if not isinstance(document, dict) or not document.get("doctype"):
		frappe.throw(_("Send one document with its DocType"), frappe.PermissionError)
	return document


def get_sent_documents() -> list[dict]:
	"""Every document in a `run_doc_method` call. Frappe v1 reads `docs`, v2 reads `document`."""
	form = frappe.local.form_dict
	return [parse_sent_document(form[key]) for key in DOCUMENT_KEYS if form.get(key)]


def get_requested_document_methods() -> list[tuple[str, str]]:
	"""Each DocType and method that a document method call can run on."""
	form = frappe.local.form_dict
	if is_document_method_call():
		doctypes = [document["doctype"] for document in get_sent_documents()]
		if form.get("dt"):
			doctypes.append(form.dt)
		return [(doctype, form.get("method")) for doctype in doctypes]
	if (requested := get_requested_method()) in DASHBOARD_METHODS:
		doctype_key, method = DASHBOARD_METHODS[requested]
		return [(form.get(doctype_key), method or form.get("method"))]
	path = get_request_path() or ""
	if match := DOCUMENT_PATH.match(path):
		return [(match.group(1), match.group(2))]
	if (match := RESOURCE_PATH.match(path)) and form.get("run_method"):
		return [(match.group(1), form.run_method)]
	return []


def check_staff_role():
	"""Stop desk staff who call a document method that their roles do not allow.

	Only the method that the request names is checked, so the same method still
	works when Press code calls it, or when a customer calls it from the dashboard.
	"""
	if not is_staff():
		return
	for doctype, method in get_requested_document_methods():
		if doctype and method and (function := getattr(get_controller(doctype), method, None)):
			check_method_roles(doctype, function)


def check_method_roles(doctype: str, function):
	"""A `needs_staff_role` method needs one of its roles. Readers call only `safe_for_readers` methods."""
	roles = getattr(function, "staff_roles", None)
	if roles and not {*roles, "System Manager"} & set(frappe.get_roles()):
		frappe.throw(_("You need one of these roles: {0}").format(", ".join(roles)), frappe.PermissionError)
	if not getattr(function, "is_safe_for_readers", False) and reads_only(doctype):
		frappe.throw(_("You can only read {0}").format(_(doctype)), frappe.PermissionError)


def reads_only(doctype: str) -> bool:
	"""Whether the user reads `doctype` only through a read-only role, such as Press Support.

	An `if_owner` row gives nothing on records of other users, so it does not count.
	"""
	perms = get_valid_perms(doctype)
	roles = {perm.role for perm in perms if perm.read and not perm.permlevel and not perm.if_owner}
	return bool(roles) and roles <= READ_ONLY_ROLES


def use_saved_document():
	"""Run a desk document method on the saved record when staff cannot write it.

	Desk sends the whole form with the call, and Frappe checks only read access
	and `modified`. Staff who cannot write a record could otherwise run its
	buttons on values they made up, or on a new record they cannot create.
	"""
	if not is_staff() or not is_document_method_call():
		return
	for key in DOCUMENT_KEYS:
		if sent := frappe.local.form_dict.get(key):
			frappe.local.form_dict[key] = get_document_to_run(parse_sent_document(sent))


def get_document_to_run(sent: dict) -> dict | str:
	doctype, name = sent.get("doctype"), sent.get("name")
	if not (name and frappe.db.exists(doctype, name)):
		if not frappe.has_permission(doctype, "create"):
			frappe.throw(_("You cannot create a {0}").format(_(doctype)), frappe.PermissionError)
		return sent
	if frappe.has_permission(doctype, "write", doc=name):
		return sent
	return frappe.get_doc(doctype, name).as_json()
