# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import annotations

import inspect
import json
import typing

import frappe
from frappe.client import set_value as _set_value
from frappe.handler import run_doc_method as _run_doc_method
from frappe.model import child_table_fields, default_fields
from frappe.model.base_document import get_controller
from frappe.monitor import add_data_to_monitor
from frappe.query_builder.terms import ValueWrapper
from frappe.utils import cstr
from pypika.queries import QueryBuilder

from press.access import dashboard_access_rules, ownership
from press.access.support_access import has_support_access
from press.exceptions import TeamHeaderNotInRequestError
from press.guards import role_guard
from press.guards.role_guard.document import has_user_permission
from press.telemetry import sentry
from press.utils import has_role

if typing.TYPE_CHECKING:
	from frappe.model.meta import Meta

ALLOWED_DOCTYPES = [
	"Site",
	"Site App",
	"Site Action",
	"Site Domain",
	"Site Backup",
	"Site Activity",
	"Server Activity",
	"Site Config",
	"Site Plan",
	"Site Update",
	"Site Group Deploy",
	"Invoice",
	"Balance Transaction",
	"Stripe Payment Method",
	"Bench",
	"Bench App",
	"Bench Dependency Version",
	"Release Group",
	"Release Group App",
	"Release Group Dependency",
	"Cluster",
	"Press Role",
	"Team",
	"Product Trial Request",
	"Deploy Candidate",
	"Deploy Candidate Difference",
	"Deploy Candidate Difference App",
	"Agent Job",
	"Agent Job Type",
	"Common Site Config",
	"Server",
	"Database Server",
	"Ansible Play",
	"Server Plan",
	"S3 Storage Plan",
	"Release Group Variable",
	"Resource Tag",
	"Press Tag",
	"Partner Approval Request",
	"Marketplace App",
	"Subscription",
	"Marketplace App Version",
	"Marketplace App Plan",
	"App Release",
	"Payout Order",
	"App Patch",
	"Product Trial",
	"Press Notification",
	"User SSH Key",
	"Frappe Version",
	"Dashboard Banner",
	"App Release Approval Request",
	"Press Webhook",
	"SQL Playground Log",
	"Site Database User",
	"Press Settings",
	"Mpesa Payment Record",
	"Razorpay Mandate",
	"Partner Certificate",
	"Partner Payment Payout",
	"Partner Tier",
	"Deploy Candidate Build",
	"Partner Lead",
	"Partner Lead Type",
	"Lead Followup",
	"Partner Consent",
	"Account Request",
	"Server Snapshot",
	"Server Snapshot Recovery",
	"Partner Lead",
	"Partner Lead Type",
	"Lead Followup",
	"Partner Consent",
	"Support Access",
	"Partner Lead Origin",
	"Auto Scale Record",
	"Server Firewall",
	"New Bench Queue",
	"Partner Audit",
	"Partner Non Conformance",
	"Team Member Resource",
	"Release Pipeline",
	"Site Plan Change",
	"Plan Change",
]

whitelisted_methods = set()


@frappe.whitelist()
def get_list(
	doctype: str,
	fields: list | None = None,
	filters: dict | None = None,
	order_by: str | None = None,
	start: int = 0,
	limit: int = 20,
	parent: str | None = None,
	debug: bool = False,
):
	if filters is None:
		filters = {}

	context_data = {
		"doctype": doctype,
		"fields": fields,
		"filters": filters,
		"order_by": order_by,
		"start": start,
		"limit": limit,
		"parent": parent,
	}
	add_data_to_monitor(
		press_api_client_method="get_list",
		press_api_client_payload=context_data,
	)
	sentry.set_context("press_client", {"method": "get_list", "data": context_data})
	check_permissions(doctype)

	valid_fields = validate_fields(doctype, fields)
	valid_filters = validate_filters(doctype, filters)

	meta = frappe.get_meta(doctype)
	if meta.istable and not (filters.get("parenttype") and filters.get("parent")):
		frappe.throw(
			"To fetch child table records, please provide both 'parenttype' and 'parent' in the filters."
		)

	apply_team_filter = not (
		filters.get("skip_team_filter_for_system_user_and_support_agent")
		and (frappe.local.system_user() or has_role("Press Support Agent"))
	)
	if apply_team_filter and meta.has_field("team"):
		valid_filters.team = frappe.local.team().name

	query = get_list_query(
		doctype,
		meta,
		filters,
		valid_filters,
		valid_fields,
		start,
		limit,
		order_by,
	)
	filters = frappe._dict(filters or {})
	list_args = dict(
		fields=fields,
		filters=filters,
		order_by=order_by,
		start=start,
		limit=limit,
		parent=parent,
		debug=debug,
	)
	query = apply_custom_filters(doctype, query, **list_args)
	if isinstance(query, QueryBuilder):
		return query.run(as_dict=1, debug=debug)

	if isinstance(query, list):
		return query

	return []


def get_list_query(
	doctype: str,
	meta: "Meta",
	filters,
	valid_filters: frappe._dict,
	valid_fields: list | None,
	start: int,
	limit: int,
	order_by: str | None,
):
	query = frappe.qb.get_query(
		doctype, filters=valid_filters, fields=valid_fields, offset=start, limit=limit, order_by=order_by
	)

	query = ownership.scope_query(doctype, meta, filters, query)

	restricted_doctypes = ("Site", "Release Group", "Server")
	if doctype in restricted_doctypes and role_guard.is_restricted() and not has_user_permission(doctype):
		permitted_documents = role_guard.permitted_documents(doctype)
		if not permitted_documents:
			query = query.where(ValueWrapper(1) == 0)  # Hack!
		else:
			QueryDoctype = frappe.qb.DocType(doctype)
			query = query.where(QueryDoctype.name.isin(permitted_documents))

	return query


@frappe.whitelist()
@role_guard.document(
	document_type=lambda args: str(args.get("doctype")),
	document_name=lambda args: str(args.get("name")),
)
def get(doctype, name):  # noqa: C901
	if frappe.request and frappe.request.path and frappe.request.path == "/api/method/press.api.client.get":
		context_data = {
			"doctype": doctype,
			"docname": name,
		}
		add_data_to_monitor(
			press_api_client_method="get_doc",
			press_api_client_payload=context_data,
		)
		sentry.set_context("press_client", {"method": "get_doc", "data": context_data})

	check_permissions(doctype)
	is_support = has_support_access(doctype, name)
	is_system_user = frappe.local.system_user()
	check_permission = not (is_system_user or is_support)

	try:
		doc = frappe.get_doc(doctype, name, check_permission=check_permission)
	except frappe.DoesNotExistError:
		controller = get_controller(doctype)
		if hasattr(controller, "on_not_found"):
			return controller.on_not_found(name)
		raise

	if not (is_system_user or is_support):
		check_document_access(doctype, name, doc=doc)

	fields = tuple(default_fields)
	if hasattr(doc, "dashboard_fields"):
		fields += tuple(doc.dashboard_fields)

	_doc = frappe._dict()
	for fieldname in fields:
		_doc[fieldname] = doc.get(fieldname)

	if hasattr(doc, "get_doc"):
		result = doc.get_doc(_doc)
		if isinstance(result, dict):
			_doc.update(result)

	return dashboard_access_rules(_doc)


@frappe.whitelist(methods=["POST", "PUT"])
def insert(doc=None):
	if not doc or not doc.get("doctype"):
		frappe.throw(frappe._("doc.doctype is required"))

	context_data = {
		"doctype": doc.get("doctype"),
		"parent": doc.get("parent"),
		"parenttype": doc.get("parenttype"),
		"parentfield": doc.get("parentfield"),
	}

	add_data_to_monitor(press_api_client_method="insert_doc", press_api_client_payload=context_data)
	sentry.set_context("press_client", {"method": "insert_doc", "data": context_data})

	check_permissions(doc.get("doctype"))

	doc = frappe._dict(doc)
	if frappe.is_table(doc.doctype):
		if not (doc.parenttype and doc.parent and doc.parentfield):
			frappe.throw(frappe._("Parenttype, Parent and Parentfield are required to insert a child record"))

		# inserting a child record
		parent = frappe.get_doc(doc.parenttype, doc.parent)
		check_document_write_access(parent.doctype, parent.name)

		parent.append(doc.parentfield, doc)
		parent.save()
		return get(parent.doctype, parent.name)

	_doc = frappe.get_doc(filter_insertable_fields(doc.doctype, doc))

	if frappe.get_meta(doc.doctype).has_field("team"):
		if not _doc.team:
			# set team if not set
			_doc.team = frappe.local.team().name
		if not frappe.local.system_user():
			# don't allow dashboard user to set any other team
			_doc.team = frappe.local.team().name

	if not frappe.local.system_user():
		# don't allow a dashboard user to create an already-submitted document
		_doc.docstatus = 0

	_doc.insert()
	return get(_doc.doctype, _doc.name)


@frappe.whitelist(methods=["POST", "PUT"])
def set_value(doctype: str, name: str, fieldname: dict | str, value: str | None = None):
	context_data = {
		"doctype": doctype,
		"docname": name,
		"fieldname": fieldname,
		"value": value,
	}

	add_data_to_monitor(press_api_client_method="set_value", press_api_client_payload=context_data)
	sentry.set_context("press_client", {"method": "set_value", "data": context_data})
	check_permissions(doctype)
	if not has_support_access(doctype, name):
		check_document_write_access(doctype, name)

	check_editable_fields(doctype, fields_being_set(fieldname, value))

	fields = fieldname if isinstance(fieldname, dict) else {fieldname: value}
	for field in fields:
		# fields mentioned in dashboard_fields are allowed to be set via set_value
		if not is_allowed_field(doctype, field):
			raise_not_permitted()

	_set_value(doctype, name, fieldname, value)

	# frappe set_value returns just the doc and not press's overriden `get_doc`
	return get(doctype, name)


@frappe.whitelist(methods=["DELETE", "POST"])
def delete(doctype: str, name: str):
	method = "delete"

	check_permissions(doctype)
	if not has_support_access(doctype, name):
		check_document_write_access(doctype, name)
	check_dashboard_actions(doctype, name, method)

	_run_doc_method(dt=doctype, dn=name, method=method, args=None)


@frappe.whitelist()
def run_doc_method(dt: str, dn: str, method: str, args: dict | None = None):
	context_data = {
		"doctype": dt,
		"docname": dn,
		"method": method,
		"args": args,
	}
	add_data_to_monitor(press_api_client_method="run_doc_method", press_api_client_payload=context_data)
	sentry.set_context("press_client", {"method": "run_doc_method", "data": context_data})

	check_permissions(dt)
	if not has_support_access(dt, dn):
		check_document_write_access(dt, dn)
	check_dashboard_actions(dt, dn, method)

	_run_doc_method(
		dt=dt,
		dn=dn,
		method=method,
		args=fix_args(method, args),
	)

	frappe.response.docs = [get(dt, dn)]


@frappe.whitelist()
def search_link(
	doctype: str,
	query: str | None = None,
	filters: dict | None = None,
	order_by: str | None = None,
	page_length: int | None = None,
):
	context_data = {
		"doctype": doctype,
		"query": query,
		"filters": filters,
		"order_by": order_by,
		"page_length": page_length,
	}

	add_data_to_monitor(press_api_client_method="search_link", press_api_client_payload=context_data)
	sentry.set_context("press_client", {"method": "search_link", "data": context_data})

	check_permissions(doctype)
	if doctype == "Team" and not frappe.local.system_user():
		raise_not_permitted()

	meta = frappe.get_meta(doctype)
	DocType = frappe.qb.DocType(doctype)
	valid_filters = validate_filters(doctype, filters)
	valid_fields = validate_fields(doctype, ["name", meta.title_field or "name"])
	q = get_list_query(
		doctype,
		meta,
		filters,
		valid_filters,
		valid_fields,
		0,
		page_length or 10,
		order_by or "modified desc",
	)
	q = q.select(DocType.name.as_("value"))
	if meta.title_field:
		q = q.select(DocType[meta.title_field].as_("label"))
	if meta.has_field("enabled"):
		q = q.where(DocType.enabled == 1)
	if meta.has_field("disabled"):
		q = q.where(DocType.disabled != 1)
	if meta.has_field("team") and (not frappe.local.system_user() or 1):
		q = q.where(DocType.team == frappe.local.team().name)
	if query:
		condition = DocType.name.like(f"%{query}%")
		if meta.title_field:
			condition = condition | DocType[meta.title_field].like(f"%{query}%")
		q = q.where(condition)
	return q.run(as_dict=1)


def check_document_access(doctype: str, name: str, doc=None):
	if frappe.local.system_user():
		return

	if not ownership.has_document_access(doctype, name, doc=doc):
		raise_not_permitted()


def check_document_write_access(doctype: str, name: str):
	# Reference data is the same for every team, so no team gets to change it.
	if doctype in ownership.GLOBAL_DOCTYPES and not frappe.local.system_user():
		raise_not_permitted()

	check_document_access(doctype, name)


def check_dashboard_actions(doctype, name, method):
	doc = frappe.get_doc(doctype, name)
	method_obj = getattr(doc, method)
	fn = getattr(method_obj, "__func__", method_obj)

	if fn not in whitelisted_methods:
		raise_not_permitted()


def apply_custom_filters(doctype, query, **list_args):
	"""Apply custom filters to query"""
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		if inspect.getfullargspec(controller.get_list_query).varkw:
			return controller.get_list_query(query, **list_args)
		return controller.get_list_query(query)

	return query


def validate_filters(doctype, filters):
	"""Filter filters based on permissions"""
	if not filters:
		filters = {}

	out = frappe._dict()
	for fieldname, value in filters.items():
		if is_allowed_field(doctype, fieldname):
			out[fieldname] = value

	return out


def validate_fields(doctype, fields):
	"""Filter fields based on permissions"""
	if not fields:
		return fields

	filtered_fields = []
	for field in fields:
		if is_allowed_field(doctype, field):
			filtered_fields.append(field)

	return filtered_fields


def is_allowed_field(doctype, field):
	"""Check if field is valid"""
	if not field:
		return False

	controller = get_controller(doctype)
	dashboard_fields = getattr(controller, "dashboard_fields", ())

	if field in dashboard_fields:
		return True

	if "." in field and is_allowed_linked_field(doctype, field):
		return True

	if isinstance(field, dict) and is_allowed_table_field(doctype, field):
		return True

	if field in [*default_fields, *child_table_fields]:
		return True

	return False


def fields_being_set(fieldname: dict | str, value: str | None) -> list[str]:
	"""The fields `frappe.client.set_value` will write, however it was called.

	It takes either a mapping or a single fieldname with its value, and a
	fieldname that parses as JSON is treated as the mapping.
	"""
	if isinstance(fieldname, dict):
		return list(fieldname)

	if value:
		return [fieldname]

	try:
		return list(json.loads(fieldname))
	except (TypeError, ValueError):
		return [fieldname]


def check_editable_fields(doctype: str, fields: list[str]):
	"""Refuse to write a field the doctype hasn't offered up for editing.

	`dashboard_fields` says what the dashboard may read, which is a much longer
	list than what it may write — a site shows its plan, server and team without
	anyone being allowed to set them from here. Doctypes name the writable ones
	in `dashboard_editable_fields`, and everything else is refused.
	"""
	editable = getattr(get_controller(doctype), "dashboard_editable_fields", ())

	for field in fields:
		if field not in editable:
			frappe.throw(f"{doctype}.{field} cannot be edited from the dashboard", frappe.PermissionError)


def is_allowed_linked_field(doctype, field):
	linked_field = linked_field_fieldname = None
	if " as " in field:
		linked_field, _ = field.split(" as ")
	else:
		linked_field = field

	linked_field, linked_field_fieldname = linked_field.split(".")
	if not is_allowed_field(doctype, linked_field):
		return False

	linked_field_doctype = frappe.get_meta(doctype).get_field(linked_field).options
	if not is_allowed_field(linked_field_doctype, linked_field_fieldname):
		return False

	return True


def is_allowed_table_field(doctype, field):
	for table_fieldname, table_fields in field.items():
		if not is_allowed_field(doctype, table_fieldname):
			return False

		table_doctype = frappe.get_meta(doctype).get_field(table_fieldname).options
		for table_field in table_fields:
			if not is_allowed_field(table_doctype, table_field):
				return False
	return True


def filter_insertable_fields(doctype, doc):
	"""Restrict a dashboard-submitted insert payload to a doctype's explicit
	create-time allowlist.

	Unlike `is_allowed_field` (used for reads and filters), this doesn't fall
	back to Frappe's `default_fields` — that list includes `docstatus`, which
	is exactly the field a dashboard user must never get to set directly.
	System users (Desk, scripts) are trusted with the full payload, as before.
	"""
	if frappe.local.system_user():
		return doc

	controller = get_controller(doctype)
	insertable_fields = getattr(controller, "dashboard_insert_fields", ())

	filtered = frappe._dict({"doctype": doctype})
	for field in insertable_fields:
		if field in doc:
			filtered[field] = doc[field]

	return filtered


def check_permissions(doctype):
	if doctype not in ALLOWED_DOCTYPES:
		raise_not_permitted()

	if not hasattr(frappe.local, "team") or not frappe.local.team():
		frappe.throw(
			"current_team is not set. Use X-PRESS-TEAM header in the request to set it.",
			TeamHeaderNotInRequestError,
		)

	return True


def is_owned_by_team(doctype, docname, raise_exception=True):
	if not frappe.local.team():
		return False

	docname = cstr(docname)
	owned = frappe.db.get_value(doctype, docname, "team") == frappe.local.team().name
	if not owned and raise_exception:
		raise_not_permitted()
	return owned


def raise_not_permitted():
	frappe.throw("Not permitted", frappe.PermissionError)


def dashboard_whitelist(allow_guest=False, xss_safe=False, methods=None):
	def wrapper(func):
		global whitelisted_methods

		decorated_func = frappe.whitelist(allow_guest=allow_guest, xss_safe=xss_safe, methods=methods)(func)

		def inner(*args, **kwargs):
			return decorated_func(*args, **kwargs)

		whitelisted_methods.add(decorated_func)
		return decorated_func

	return wrapper


def fix_args(method, args):
	# This is a fixer function. Certain callers of `run_doc_method`
	# pass duplicates of the passed kwargs in the `args` arg.
	#
	# This causes "got multiple values for argument 'method'"
	if not isinstance(args, dict):
		return args

	# Even if it doesn't match it'll probably throw
	# down the call stack, but in that case it's unexpected
	# behavior and so it's better to error-out.
	if args.get("method") == method:
		del args["method"]

	return args
