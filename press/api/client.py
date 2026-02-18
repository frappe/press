# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import annotations

import inspect
import typing

import frappe
from frappe.client import set_value as _set_value
from frappe.handler import run_doc_method as _run_doc_method
from frappe.model import child_table_fields, default_fields
from frappe.model.base_document import get_controller
from frappe.utils import cstr
from pypika.queries import QueryBuilder

from press.access import dashboard_access_rules
from press.access.support_access import has_support_access
from press.exceptions import TeamHeaderNotInRequestError
from press.guards import role_guard
from press.utils import has_role

if typing.TYPE_CHECKING:
	from frappe.model.meta import Meta

ALLOWED_DOCTYPES = [
	"Site",
	"Site App",
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
	"Press Permission Group",
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
	"Partner Certificate",
	"Partner Payment Payout",
	"Deploy Candidate Build",
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

	# these doctypes doesn't have a team field to filter by but are used in get or run_doc_method
	if doctype in ["Team", "User SSH Key"]:
		return []

	check_permissions(doctype)
	valid_fields = validate_fields(doctype, fields)
	valid_filters = validate_filters(doctype, filters)

	meta = frappe.get_meta(doctype)
	if meta.istable and not (filters.get("parenttype") and filters.get("parent")):
		frappe.throw("parenttype and parent are required to get child records")

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
	filters: dict,
	valid_filters: frappe._dict,
	valid_fields: list | None,
	start: int,
	limit: int,
	order_by: str | None,
):
	query = frappe.qb.get_query(
		doctype,
		filters=valid_filters,
		fields=valid_fields,
		offset=start,
		limit=limit,
		order_by=order_by,
	)

	if meta.istable and frappe.get_meta(filters.get("parenttype")).has_field("team"):
		ParentDocType = frappe.qb.DocType(filters.get("parenttype"))
		ChildDocType = frappe.qb.DocType(doctype)

		query = (
			query.join(ParentDocType)
			.on(ParentDocType.name == ChildDocType.parent)
			.where(ParentDocType.team == frappe.local.team().name)
		)

	restricted_doctypes = ("Site", "Release Group", "Server")
	if doctype in restricted_doctypes and role_guard.is_restricted():
		permitted_documents = role_guard.permitted_documents(doctype)
		if not permitted_documents:
			return []
		QueryDoctype = frappe.qb.DocType(doctype)
		query = query.where(QueryDoctype.name.isin(permitted_documents))

	return query


@frappe.whitelist()
@role_guard.document(
	document_type=lambda args: str(args.get("doctype")),
	document_name=lambda args: str(args.get("name")),
)
def get(doctype, name):
	check_permissions(doctype)
	try:
		doc = frappe.get_doc(doctype, name)
	except frappe.DoesNotExistError:
		controller = get_controller(doctype)
		if hasattr(controller, "on_not_found"):
			return controller.on_not_found(name)
		raise

	if (
		not (frappe.local.system_user() or has_support_access(doctype, name))
		and frappe.get_meta(doctype).has_field("team")
		and doc.team != frappe.local.team().name
	):
		raise_not_permitted()

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

	check_permissions(doc.get("doctype"))

	doc = frappe._dict(doc)
	if frappe.is_table(doc.doctype):
		if not (doc.parenttype and doc.parent and doc.parentfield):
			frappe.throw(frappe._("Parenttype, Parent and Parentfield are required to insert a child record"))

		# inserting a child record
		parent = frappe.get_doc(doc.parenttype, doc.parent)

		if frappe.get_meta(parent.doctype).has_field("team") and parent.team != frappe.local.team().name:
			raise_not_permitted()

		parent.append(doc.parentfield, doc)
		parent.save()
		return get(parent.doctype, parent.name)

	_doc = frappe.get_doc(doc)

	if frappe.get_meta(doc.doctype).has_field("team"):
		if not _doc.team:
			# set team if not set
			_doc.team = frappe.local.team().name
		if not frappe.local.system_user():
			# don't allow dashboard user to set any other team
			_doc.team = frappe.local.team().name
	_doc.insert()
	return get(_doc.doctype, _doc.name)


@frappe.whitelist(methods=["POST", "PUT"])
def set_value(doctype: str, name: str, fieldname: dict | str, value: str | None = None):
	check_permissions(doctype)
	check_document_access(doctype, name)

	for field in fieldname:
		# fields mentioned in dashboard_fields are allowed to be set via set_value
		is_allowed_field(doctype, field)

	_set_value(doctype, name, fieldname, value)

	# frappe set_value returns just the doc and not press's overriden `get_doc`
	return get(doctype, name)


@frappe.whitelist(methods=["DELETE", "POST"])
def delete(doctype: str, name: str):
	method = "delete"

	check_permissions(doctype)
	check_document_access(doctype, name)
	check_dashboard_actions(doctype, name, method)

	_run_doc_method(dt=doctype, dn=name, method=method, args=None)


@frappe.whitelist()
def run_doc_method(dt: str, dn: str, method: str, args: dict | None = None):
	check_permissions(dt)
	check_document_access(dt, dn)
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


def check_document_access(doctype: str, name: str):
	if frappe.local.system_user():
		return

	team = ""
	meta = frappe.get_meta(doctype)
	if meta.has_field("team"):
		team = frappe.db.get_value(doctype, name, "team")
	elif meta.has_field("bench"):
		bench = frappe.db.get_value(doctype, name, "bench")
		team = frappe.db.get_value("Bench", bench, "team")
	elif meta.has_field("group"):
		group = frappe.db.get_value(doctype, name, "group")
		team = frappe.db.get_value("Release Group", group, "team")
	else:
		return

	if team == frappe.local.team().name:
		return

	if has_support_access(doctype, name):
		return

	raise_not_permitted()


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
