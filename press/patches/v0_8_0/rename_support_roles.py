import frappe

ROLES = {"Press Support Agent": "Press Employee", "Press Support": "Press Support L1"}
ROLE_PROFILES = {"Press Support": "Press Support L1"}


def execute():
	"""Rename the two support roles, so that each name says who holds it.
	Press Employee is for every employee. Press Support L1 is first-line support."""
	for old, new in ROLES.items():
		rename("Role", old, new)
	for old, new in ROLE_PROFILES.items():
		if rename("Role Profile", old, new):
			frappe.db.set_value("Role Profile", new, "role_profile", new)  # Its autoname does not follow


def rename(doctype: str, old: str, new: str) -> bool:
	if not frappe.db.exists(doctype, old) or frappe.db.exists(doctype, new):
		return False
	frappe.rename_doc(doctype, old, new, force=True)
	return True
