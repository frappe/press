import frappe
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder, document_type: str, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRolePermission = frappe.qb.DocType("Press Role Permission")

	return (
		base_query.left_join(PressRolePermission)
		.on(PressRolePermission.team == PressRole.team & PressRolePermission.role == PressRole.name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRolePermission[document_type.lower().replace(" ", "_")] == document_name)
		.run(as_dict=True, pluck="count")
		.pop()
		> 0
	)
