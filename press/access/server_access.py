"""Whether desk staff may get a shell on a server: Ansible, the serial console or SSH.

Shared servers hold the sites of many teams, so only System Managers reach them.
Other servers need membership of the owning team, or its consent.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from press.access.support_access import is_insider


def can_reach_server(doctype: str, name: str) -> bool:
	if "System Manager" in frappe.get_roles():
		return True
	server = frappe.db.get_value(doctype, name, ["public", "team"], as_dict=True)
	if not server or server.public:
		return False
	return is_insider(server.team) or has_server_consent(doctype, name)


def has_server_consent(doctype: str, name: str) -> bool:
	"""An accepted Support Access with Server SSH that the session user requested, on a covering server."""
	servers = consenting_servers(doctype, name)
	if not servers:
		return False
	filters = [
		["status", "=", "Accepted"],
		["access_allowed_till", ">", now_datetime()],
		["server_ssh", "=", 1],
		["requested_by", "=", frappe.session.user],
		["Support Access Resource", "document_type", "=", "Server"],
		["Support Access Resource", "document_name", "in", servers],
	]
	return bool(frappe.get_all("Support Access", filters=filters, limit=1))


def consenting_servers(doctype: str, name: str) -> list[str]:
	"""The app servers whose Support Access covers `name`. A grant names the app server of a pair."""
	if doctype == "Server":
		return [name]
	if doctype == "Database Server":
		# Only servers of the same team, so one team cannot consent for another team's database
		team = frappe.db.get_value("Database Server", name, "team")
		if not team:
			return []
		return frappe.get_all("Server", {"database_server": name, "team": team}, pluck="name")
	return []


def check_server_access(doctype: str, name: str) -> None:
	if not can_reach_server(doctype, name):
		frappe.throw(
			_(
				"You cannot reach {0} {1}. Shared servers need a System Manager. Other servers need the"
				" consent of their team: request Support Access with Server SSH from the dashboard."
			).format(doctype, name),
			frappe.PermissionError,
		)
