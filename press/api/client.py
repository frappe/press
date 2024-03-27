# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import inspect

import frappe
from frappe import is_whitelisted
from frappe.client import delete_doc, set_value as _set_value
from frappe.handler import get_attr
from frappe.handler import run_doc_method as _run_doc_method
from frappe.model import child_table_fields, default_fields
from frappe.model.base_document import get_controller
from frappe.utils import cstr
from pypika.queries import QueryBuilder

ALLOWED_DOCTYPES = [
	"Site",
	"Site App",
	"Site Domain",
	"Site Backup",
	"Site Activity",
	"Site Config",
	"Site Config Key",
	"Site Plan",
	"Site Update",
	"Invoice",
	"Balance Transaction",
	"Stripe Payment Method",
	"Bench",
	"Bench Dependency Version",
	"Release Group",
	"Release Group App",
	"Release Group Dependency",
	"Cluster",
	"Press Permission Group",
	"Team",
	"SaaS Product Site Request",
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
	"User",
	"Partner Approval Request",
	"Marketplace App",
	"Subscription",
	"Marketplace App Version",
	"Marketplace App Plan",
	"App Release",
	"Payout Order",
	"App Patch",
	"SaaS Product",
	"Press Notification",
	"User SSH Key",
	"Frappe Version",
]


@frappe.whitelist()
def get_list(
	doctype,
	fields=None,
	filters=None,
	order_by=None,
	start=0,
	limit=20,
	parent=None,
	debug=False,
):
	if filters is None:
		filters = {}
	check_permissions(doctype)
	valid_fields = validate_fields(doctype, fields)
	valid_filters = validate_filters(doctype, filters)

	meta = frappe.get_meta(doctype)
	if meta.istable and not (filters.get("parenttype") and filters.get("parent")):
		frappe.throw("parenttype and parent are required to get child records")

	apply_team_filter = not (
		filters.get("skip_team_filter_for_system_user") and frappe.local.system_user()
	)
	if apply_team_filter and meta.has_field("team"):
		valid_filters.team = frappe.local.team().name

	query = frappe.qb.get_query(
		doctype,
		filters=valid_filters,
		fields=valid_fields,
		offset=start,
		limit=limit,
		order_by=order_by,
	)

	if meta.istable:
		parentmeta = frappe.get_meta(filters.get("parenttype"))
		if parentmeta.has_field("team"):
			ParentDocType = frappe.qb.DocType(filters.get("parenttype"))
			ChildDocType = frappe.qb.DocType(doctype)
			query = (
				query.join(ParentDocType)
				.on(ParentDocType.name == ChildDocType.parent)
				.where(ParentDocType.team == frappe.local.team().name)
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
	elif isinstance(query, list):
		return query
	elif query is None:
		return []


@frappe.whitelist()
def get(doctype, name):
	check_permissions(doctype)
	check_method_permissions(
		doctype, name, "get_doc", "You don't have permission to view this document"
	)
	try:
		doc = frappe.get_doc(doctype, name)
	except frappe.DoesNotExistError:
		controller = get_controller(doctype)
		if hasattr(controller, "on_not_found"):
			return controller.on_not_found(name)
		raise

	if not frappe.local.system_user() and frappe.get_meta(doctype).has_field("team"):
		if doc.team != frappe.local.team().name:
			raise_not_permitted()

	fields = list(default_fields)
	if hasattr(doc, "dashboard_fields"):
		fields += doc.dashboard_fields

	_doc = frappe._dict()
	for fieldname in fields:
		_doc[fieldname] = doc.get(fieldname)

	if hasattr(doc, "get_doc"):
		result = doc.get_doc(_doc)
		if isinstance(result, dict):
			_doc.update(result)

	return _doc


@frappe.whitelist(methods=["POST", "PUT"])
def insert(doc=None):
	if not doc or not doc.get("doctype"):
		frappe.throw(frappe._("doc.doctype is required"))

	check_permissions(doc.get("doctype"))

	doc = frappe._dict(doc)
	if frappe.is_table(doc.doctype):
		if not (doc.parenttype and doc.parent and doc.parentfield):
			frappe.throw(
				frappe._("Parenttype, Parent and Parentfield are required to insert a child record")
			)

		# inserting a child record
		parent = frappe.get_doc(doc.parenttype, doc.parent)

		if frappe.get_meta(parent.doctype).has_field("team"):
			if parent.team != frappe.local.team().name:
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
def set_value(doctype, name, fieldname, value=None):
	check_permissions(doctype)
	check_team_access(doctype, name)

	for field in fieldname.keys():
		# fields mentioned in whitelisted_actions are allowed to be set via set_value
		check_dashboard_actions(doctype, field)

	return _set_value(doctype, name, fieldname, value)


@frappe.whitelist(methods=["DELETE", "POST"])
def delete(doctype, name):
	check_permissions(doctype)
	check_team_access(doctype, name)
	check_dashboard_actions(doctype, "delete")

	delete_doc(doctype, name)


@frappe.whitelist()
def run_doc_method(dt, dn, method, args=None):
	check_permissions(dt)
	check_team_access(dt, dn)
	check_dashboard_actions(dt, method)
	check_method_permissions(dt, dn, method)

	_run_doc_method(dt=dt, dn=dn, method=method, args=args)
	frappe.response.docs = [get(dt, dn)]


@frappe.whitelist()
def search_link(doctype, query=None, filters=None, order_by=None, page_length=None):
	check_permissions(doctype)
	meta = frappe.get_meta(doctype)
	DocType = frappe.qb.DocType(doctype)
	valid_filters = validate_filters(doctype, filters)
	q = frappe.qb.get_query(
		doctype,
		filters=valid_filters,
		offset=0,
		limit=page_length or 10,
		order_by=order_by or "modified desc",
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


def check_team_access(doctype: str, name: str):
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

	raise_not_permitted()


def check_dashboard_actions(doctype, method):
	controller = get_controller(doctype)
	dashboard_actions = getattr(controller, "dashboard_actions", [])
	if method in dashboard_actions:
		return

	raise_not_permitted()


@frappe.whitelist()
def run_doctype_method(doctype, method, **kwargs):
	check_permissions(doctype)

	from frappe.modules.utils import get_doctype_module, get_module_name

	module = get_doctype_module(doctype)
	method_path = get_module_name(doctype, module, "", "." + method)

	try:
		_function = get_attr(method_path)
	except Exception as e:
		frappe.throw(
			frappe._("Failed to get method for command {0} with {1}").format(method_path, e)
		)

	is_whitelisted(_function)

	return frappe.call(_function, **kwargs)


def apply_custom_filters(doctype, query, **list_args):
	"""Apply custom filters to query"""
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		if inspect.getfullargspec(controller.get_list_query).varkw:
			return controller.get_list_query(query, **list_args)
		else:
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
	dashboard_fields = getattr(controller, "dashboard_fields", [])

	if field in dashboard_fields:
		return True
	elif "." in field and is_allowed_linked_field(doctype, field):
		return True
	elif isinstance(field, dict) and is_allowed_table_field(doctype, field):
		return True
	elif field in [*default_fields, *child_table_fields]:
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

	if not frappe.local.team():
		frappe.throw(
			"current_team is not set. Use X-PRESS-TEAM header in the request to set it."
		)

	return True


def check_method_permissions(doctype, docname, method, error_message=None) -> None:
	from press.press.doctype.press_permission_group.press_permission_group import (
		has_method_permission,
	)

	if not has_method_permission(doctype, docname, method):
		frappe.throw(error_message or f"{method} is not permitted on {doctype} {docname}")
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
