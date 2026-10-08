import frappe
from frappe.query_builder.terms import QueryBuilder

from .document import check as document_check


def check(base_query: QueryBuilder, document_name: str) -> bool:
	servers = frappe.get_all("Server", {"database_server": document_name}, pluck="name")
	return any(document_check(base_query, "Server", server) for server in servers)
