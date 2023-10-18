# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from pypika.queries import QueryBuilder
from frappe.model.base_document import get_controller
from frappe.model import default_fields


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


def apply_custom_filters(doctype, query, **list_args):
	"""Apply custom filters to query"""
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		return_value = controller.get_list_query(query, **list_args)
		if return_value is not None:
			query = return_value

	return query


def filter_fields(doctype, fields):
	"""Filter fields based on permissions"""
	if not fields:
		return fields
	meta = frappe.get_meta(doctype)
	filtered_fields = []
	for field in fields:
		if field == "*" or "." in field:
			filtered_fields.append(field)
		elif meta.has_field(field) or field in default_fields:
			filtered_fields.append(field)

	return filtered_fields
