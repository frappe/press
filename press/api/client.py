# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import inspect
from pypika.queries import QueryBuilder
from frappe.model.base_document import get_controller
from frappe.model import default_fields, child_table_fields
from frappe import is_whitelisted
from frappe.handler import get_attr, run_doc_method as _run_doc_method
from press.press.doctype.press_permission_group.press_permission_group import (
	get_permitted_methods,
)


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
	check_permissions(doctype)
	valid_fields = validate_fields(doctype, fields)
	valid_filters = validate_filters(doctype, filters)

	if not frappe.local.system_user() and frappe.get_meta(doctype).has_field("team"):
		valid_filters = valid_filters or frappe._dict()
		valid_filters.team = frappe.local.team().name

	query = frappe.qb.get_query(
		doctype,
		filters=valid_filters,
		fields=valid_fields,
		offset=start,
		limit=limit,
		order_by=order_by,
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
	doc = frappe.get_doc(doctype, name)

	if not frappe.local.system_user() and frappe.get_meta(doctype).has_field("team"):
		if doc.team != frappe.local.team().name:
			frappe.throw("Not permitted", frappe.PermissionError)

	fields = list(default_fields)
	if hasattr(doc, "whitelisted_fields"):
		fields += doc.whitelisted_fields

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
		parent.append(doc.parentfield, doc)
		parent.save()
		return parent

	_doc = frappe.get_doc(doc)
	if not frappe.local.system_user() and frappe.get_meta(doc.doctype).has_field("team"):
		# don't allow non system user to set any other team
		_doc.team = frappe.local.team().name
	_doc.insert()
	return get(_doc.doctype, _doc.name)


@frappe.whitelist(methods=["POST", "PUT"])
def set_value(doctype, name, fieldname, value=None):
	pass


@frappe.whitelist(methods=["DELETE", "POST"])
def delete(doctype, name):
	pass


@frappe.whitelist()
def run_doc_method(dt, dn, method, args=None):
	check_permissions(dt)
	_run_doc_method(dt=dt, dn=dn, method=method, args=args)
	frappe.response.docs = [get(dt, dn)]


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
		return filters

	out = {}
	for fieldname, value in filters.items():
		if is_valid_field(doctype, fieldname):
			out[fieldname] = value

	return out


def validate_fields(doctype, fields):
	"""Filter fields based on permissions"""
	if not fields:
		return fields

	filtered_fields = []
	for field in fields:
		if is_valid_field(doctype, field):
			filtered_fields.append(field)

	return filtered_fields


def is_valid_field(doctype, field):
	"""Check if field is valid"""
	if not field:
		return False

	if field == "*" or "." in field:
		return True
	elif isinstance(field, dict) or field in [*default_fields, *child_table_fields]:
		return True
	elif df := frappe.get_meta(doctype).get_field(field):
		if df.fieldtype not in frappe.model.table_fields:
			return True

	return False


def check_permissions(doctype):
	# TODO: remove this when we have proper permission checking
	if not (frappe.conf.developer_mode or frappe.local.dev_server):
		frappe.only_for("System Manager")

	if not frappe.local.team():
		frappe.throw(
			"current_team is not set. Use X-PRESS-TEAM header in the request to set it."
		)

	return True
