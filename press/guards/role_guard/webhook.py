import frappe
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder


def check(base_query: QueryBuilder) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	return (
		base_query.where(PressRole.allow_webhook_configuration == 1)
		.select(Count(PressRole.name).as_("count"))
		.run(as_dict=True, pluck="count")
		.pop()
		> 0
	)
