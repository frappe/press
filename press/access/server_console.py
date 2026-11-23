"""Who may open a console on a server: the Ansible Console, or the serial console of its VM.

System Managers reach every server. Press Infrastructure Manager reaches only the servers that
`check_server_access` allows.
"""

import frappe
from frappe import _

from press.access.server_access import check_server_access

CONSOLE_ROLES = ["System Manager", "Press Infrastructure Manager"]
CONSOLE_DOCTYPES = ("Server", "Database Server", "Proxy Server")


def has_system_manager_role() -> bool:
	return "System Manager" in frappe.get_roles()


def check_console_role() -> None:
	frappe.only_for(CONSOLE_ROLES, message=True)


def check_console_access(doctype: str, name: str) -> None:
	"""Refuse a console on `name` unless the session may reach it."""
	check_console_role()
	if has_system_manager_role():
		return
	if doctype not in CONSOLE_DOCTYPES:
		frappe.throw(
			_("Only System Managers can open a console on {0} {1}").format(doctype, name),
			frappe.PermissionError,
		)
	check_server_access(doctype, name)
