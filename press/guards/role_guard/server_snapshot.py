import frappe
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleResource = frappe.qb.DocType("Press Role Resource")
	ServerSnapshot = frappe.qb.DocType("Server Snapshot")
	return (
		base_query.left_join(PressRoleResource)
		.on(PressRoleResource.parent == PressRole.name)
		.left_join(ServerSnapshot)
		.on(ServerSnapshot.name == document_name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRoleResource.document_type == "Server")
		.where(PressRoleResource.document_name == ServerSnapshot.app_server)
		.run(as_dict=True)
		.pop()
		.get("count")
		> 0
	)
