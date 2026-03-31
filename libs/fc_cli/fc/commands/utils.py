from __future__ import annotations


def get_doctype(name: str) -> str:
	"""Infer doctype from a server name."""
	return "Server" if name and name.startswith("f") else "Database Server"


def validate_server_name(name: str) -> tuple[bool, str | None]:
	"""Validate server name format. Returns (is_valid, error_message)."""
	if not name:
		return False, "Server name is required"
	if not name.endswith("frappe.cloud"):
		return False, "Invalid server name. It must end with 'frappe.cloud'"
	return True, None
