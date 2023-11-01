# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import inspect
from pypika.queries import QueryBuilder
from frappe.model.base_document import get_controller
from frappe.model import default_fields
from frappe import is_whitelisted
from frappe.handler import get_attr


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
	filtered_fields = filter_fields(doctype, fields)
	query = frappe.qb.get_query(
		doctype,
		filters=filters,
		fields=filtered_fields,
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

	out = {}
	for fieldname in default_fields:
		out[fieldname] = doc.get(fieldname)
	if hasattr(doc, "get_doc"):
		out.update(doc.get_doc())

	return out


@frappe.whitelist()
def insert(doc):
	pass


@frappe.whitelist(methods=["POST", "PUT"])
def set_value(doctype, name, fieldname, value=None):
	pass


@frappe.whitelist(methods=["DELETE", "POST"])
def delete(doctype, name):
	pass


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


def filter_fields(doctype, fields):
	"""Filter fields based on permissions"""
	if not fields:
		return fields
	meta = frappe.get_meta(doctype)
	filtered_fields = []
	for field in fields:
		if not field:
			continue
		if field == "*" or "." in field:
			filtered_fields.append(field)
		elif isinstance(field, dict) or field in default_fields:
			filtered_fields.append(field)
		elif df := meta.get_field(field):
			if df.fieldtype not in frappe.model.table_fields:
				filtered_fields.append(field)

	return filtered_fields


def check_permissions(doctype):
	# TODO: remove this when we have proper permission checking
	if not (frappe.conf.developer_mode or frappe.local.dev_server):
		frappe.only_for("System Manager")

	if not frappe.local.team:
		frappe.throw(
			"current_team is not set. Use X-PRESS-TEAM header in the request to set it."
		)

	return True
