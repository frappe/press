import frappe
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleResource = frappe.qb.DocType("Press Role Resource")
	SiteBackup = frappe.qb.DocType("Site Backup")
	return (
		base_query.left_join(PressRoleResource)
		.on(PressRoleResource.parent == PressRole.name)
		.left_join(SiteBackup)
		.on(SiteBackup.name == document_name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRoleResource.document_type == "Site")
		.where(PressRoleResource.document_name == SiteBackup.site)
		.run(as_dict=True)
		.pop()
		.get("count")
		> 0
	)
