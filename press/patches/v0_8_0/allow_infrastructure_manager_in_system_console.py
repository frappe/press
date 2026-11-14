import frappe
from frappe.permissions import add_permission, update_permission_property

ROLE = "Press Infrastructure Manager"


def execute():
	"""Let the Press Infrastructure Manager role open the System Console in desk, and read its own Console Logs."""
	create_role()
	# Without write, desk shows the console field read-only, so no one can type a query
	add_rule("System Console", "write")
	add_rule("Console Log", "if_owner")


def create_role():
	# Fixtures sync after patches, and a Custom DocPerm links to its role
	if not frappe.db.exists("Role", ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert()


def add_rule(doctype: str, extra_right: str):
	"""A read rule for the role on `doctype`, with `extra_right` also set."""
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": ROLE, "permlevel": 0}):
		add_permission(doctype, ROLE)
	update_permission_property(doctype, ROLE, 0, extra_right, 1)
