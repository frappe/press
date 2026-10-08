import frappe
from frappe.query_builder.terms import QueryBuilder

from .document import check as document_check


def check(base_query: QueryBuilder, document_name: str) -> bool:
	group = frappe.db.get_value("Bench", document_name, "group")
	return bool(group) and document_check(base_query, "Release Group", group)
