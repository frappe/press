import frappe

from press.utils import _system_user, is_user_part_of_team


def is_public_resource(doctype: str, docname: str) -> bool:
	if not frappe.get_meta(doctype).has_field("public"):
		return False

	return bool(frappe.get_value(doctype, docname, "public"))


def is_outside_employee(team: str | None) -> bool:
	"""A system user who does not belong to `team`, though they can switch into it."""
	if frappe.session.user == "Administrator" or not _system_user():
		return False
	return not (team and is_user_part_of_team(frappe.session.user, team))
