import frappe
from frappe.query_builder.terms import QueryBuilder

from .document import check as document_check


def check(base_query: QueryBuilder, document_name: str) -> bool:
	servers = frappe.get_all("Server", {"database_server": primary(document_name)}, pluck="name")
	return any(document_check(base_query, "Server", server) for server in servers)


def primary(database_server: str) -> str:
	# App servers point at the primary, so a replica takes the grants of its primary.
	return frappe.db.get_value("Database Server", database_server, "primary") or database_server
