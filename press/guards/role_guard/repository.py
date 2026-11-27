import frappe
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder) -> set[str] | None:
	"""Lowercased owner/name of the repositories the roles grant, or None when a role grants all."""
	if grants_all(base_query):
		return None
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleRepository = frappe.qb.DocType("Press Role Repository")
	rows = (
		base_query.inner_join(PressRoleRepository)
		.on(PressRoleRepository.parent == PressRole.name)
		.select(PressRoleRepository.repository)
		.run(as_dict=True)
	)
	return {row.repository.lower() for row in rows}


def grants_all(base_query: QueryBuilder) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	return (
		base_query.where(PressRole.all_repositories == 1)
		.select(Count(PressRole.name).as_("count"))
		.run(as_dict=True)
		.pop()
		.get("count")
		> 0
	)
