import frappe
from frappe import _

from press.utils import _system_user, is_user_part_of_team
from press.utils.user import is_employee


def is_public_resource(doctype: str, docname: str) -> bool:
	if not frappe.get_meta(doctype).has_field("public"):
		return False

	return bool(frappe.get_value(doctype, docname, "public"))


def is_outside_employee(team: str | None) -> bool:
	"""An employee who does not belong to `team`. System Managers, Administrator among
	them, are exempt from every employee check, except on the dashboard."""
	if not is_employee() or (_system_user() and "System Manager" in frappe.get_roles()):
		return False
	return not (team and is_user_part_of_team(frappe.session.user, team))


def refuse_backup_download() -> None:
	"""The one error for an employee downloading another team's backups."""
	frappe.throw(
		_("Employees cannot download the backups of a site that belongs to another team."),
		frappe.PermissionError,
	)
