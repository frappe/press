import frappe
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRolePermission = frappe.qb.DocType("Press Role Permission")
	ServerSnapshot = frappe.qb.DocType("Server Snapshot")
	return (
		base_query.left_join(PressRolePermission)
		.on(PressRolePermission.team == PressRole.team & PressRolePermission.role == PressRole.name)
		.left_join(ServerSnapshot)
		.on(ServerSnapshot.name == document_name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRolePermission.server == ServerSnapshot.app_server)
		.run(as_dict=True, pluck="count")
		.pop()
		> 0
	)
