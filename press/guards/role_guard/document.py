import frappe
from frappe.query_builder import Not
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder, document_type: str, document_name: str) -> bool | list[str]:
	if document_name:
		return document(base_query, document_type, document_name)
	return documents(base_query, document_type)


def documents(base_query: QueryBuilder, document_type: str) -> list[str]:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleResource = frappe.qb.DocType("Press Role Resource")
	return [
		doc.document_name
		for doc in base_query.inner_join(PressRoleResource)
		.on(
			(PressRoleResource.parent == PressRole.name)
			& (PressRoleResource.document_type == document_type)
			& (Not(PressRoleResource.document_name.isnull()))
		)
		.select(PressRoleResource.document_name)
		.distinct()
		.run(as_dict=True)
	]


def document(base_query: QueryBuilder, document_type: str, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleResource = frappe.qb.DocType("Press Role Resource")
	return (
		base_query.inner_join(PressRoleResource)
		.on(
			(PressRoleResource.parent == PressRole.name)
			& (PressRoleResource.document_type == document_type)
			& (PressRoleResource.document_name == document_name)
		)
		.select(Count(PressRole.name).as_("document_count"))
		.run(as_dict=True)
		.pop()
		.get("document_count")
		> 0
	)
