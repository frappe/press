"""Staff access to the resources of an open incident, without the consent of their team.

During an incident nobody from the team is there to accept a Support Access request. SREs and
L2 support reach the servers of a recent open incident, and the benches and sites on them, until
the incident is resolved. Login as Administrator still needs consent. Role checks still apply.
"""

import frappe
from frappe.utils import add_to_date, cstr, now_datetime

INCIDENT_ROLES = {"Press Infrastructure Manager", "Press Support Engineer"}
ACTIVE_STATUSES = ("Confirmed", "Acknowledged", "Investigating")
# An incident that nobody closed must not open its servers for good
ACTIVE_HOURS = 6
SERVER_DOCTYPES = ("Server", "Database Server", "Proxy Server")
# Doctypes that run on one server, by the field that names it
SERVER_FIELDS = {"Site": "server", "Bench": "server", "Agent Job": "server"}


def has_incident_access(*resources: tuple[str, str]) -> bool:
	"""Whether one of `resources` runs on a server of an open incident, and the session user responds to it."""
	if not INCIDENT_ROLES & set(frappe.get_roles()):
		return False
	servers = incident_servers()
	return bool(servers) and any(runs_on(doctype, name, servers) for doctype, name in resources)


def runs_on(doctype: str, name: str, servers: set[str]) -> bool:
	if doctype in SERVER_DOCTYPES:
		return name in servers
	if doctype == "Release Group":
		return group_runs_only_on(name, servers)
	if doctype in SERVER_FIELDS:
		return frappe.db.get_value(doctype, name, SERVER_FIELDS[doctype]) in servers
	return False


def group_runs_only_on(group: str, servers: set[str]) -> bool:
	"""Access to a group covers all its benches, so every active bench must be on an incident server."""
	bench_servers = set(frappe.get_all("Bench", {"group": group, "status": "Active"}, pluck="server"))
	return bool(bench_servers) and bench_servers <= servers


def incident_servers() -> set[str]:
	"""The servers of every open incident from the last `ACTIVE_HOURS` hours.

	Only incidents that monitoring created count, so staff cannot open a server by creating one.
	"""
	incidents = frappe.get_all(
		"Incident",
		filters={
			"owner": "Administrator",
			"server": ("is", "set"),
			"status": ("in", ACTIVE_STATUSES),
			"creation": (">", add_to_date(now_datetime(), hours=-ACTIVE_HOURS)),
		},
		fields=["server", "resource_type", "resource"],
	)
	return {server for incident in incidents for server in affected_servers(incident)}


def affected_servers(incident: frappe._dict) -> set[str]:
	"""The app server of an incident, its database server, and its proxy when the incident names it."""
	server = cstr(incident.server)
	database_server = frappe.get_cached_value("Server", server, "database_server")
	proxy_server = frappe.get_cached_value("Server", server, "proxy_server")
	servers = {server, database_server}
	if incident.resource_type == "Proxy Server" and incident.resource == proxy_server:
		servers.add(proxy_server)
	return {cstr(name) for name in servers if name}
