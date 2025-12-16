import frappe
from frappe.query_builder import Not
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder

from .utils import document_type_key


def check(base_query: QueryBuilder, document_type: str, document_name: str) -> bool | list[str]:
	if document_name:
		return documents(base_query, document_type)
	return document(base_query, document_type, document_name)


def documents(base_query: QueryBuilder, document_type: str) -> list[str]:
	PressRole = frappe.qb.DocType("Press Role")
	PressRolePermission = frappe.qb.DocType("Press Role Permission")
	document_key = document_type_key(document_type)
	return (
		base_query.inner_join(PressRolePermission)
		.on(
			(PressRolePermission.team == PressRole.team)
			& (PressRolePermission.role == PressRole.name)
			& (Not(PressRolePermission[document_key].isnull()))
		)
		.select(PressRolePermission[document_key].as_("name"))
		.distinct()
		.run(as_dict=True, pluck="name")
	)


def document(base_query: QueryBuilder, document_type: str, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRolePermission = frappe.qb.DocType("Press Role Permission")
	document_key = document_type_key(document_type)
	return (
		base_query.inner_join(PressRolePermission)
		.on(PressRolePermission.team == PressRole.team & PressRolePermission.role == PressRole.name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRolePermission[document_key] == document_name)
		.run(as_dict=True)
		.pop()
		.get("count")
		> 0
	)
