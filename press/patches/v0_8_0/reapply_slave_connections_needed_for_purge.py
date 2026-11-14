import json

import frappe

from press.agent import Agent
from press.press.doctype.database_server.database_server import DatabaseServer
from press.utils import log_error

VARIABLE = "slave_connections_needed_for_purge"


def execute():
	"""The first rollout sent None instead of 0, so MariaDB 11.8 never purges binlogs."""
	for server in servers_with_failed_rollout():
		try:
			if needs_fix(server):
				reapply(server)
				print(f"Set {VARIABLE} to 0: {server}")
		except Exception:
			# one unreachable server must not stop the run
			log_error("Reapply Purge Variable Patch Failure", server=server)


def servers_with_failed_rollout() -> list[str]:
	plays = frappe.get_all(
		"Ansible Play",
		filters={"play": "Set mysqld variable", "variables": ("like", f"%{VARIABLE}%")},
		fields=["server", "variables"],
		order_by="creation asc",
	)
	latest = {play.server: json.loads(play.variables).get("value") for play in plays}
	return [server for server, value in latest.items() if value is None]


def needs_fix(server: str) -> bool:
	if frappe.db.get_value("Database Server", server, "status") != "Active":
		return False
	# 10.6 lacks the variable, and setting it there breaks frappe.cnf
	rows = Agent(server, "Database Server").fetch_database_variables()
	value = next((row["Value"] for row in rows if row["Variable_name"] == VARIABLE), None)
	return value not in (None, "0")


def reapply(server: str):
	# The row already holds 0; only the play that applied it failed
	database_server = DatabaseServer("Database Server", server)
	variable = next(v for v in database_server.mariadb_system_variables if v.mariadb_variable == VARIABLE)
	variable.update_on_server()
