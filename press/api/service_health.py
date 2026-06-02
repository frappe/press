import contextlib
from typing import TYPE_CHECKING

import frappe
from frappe.utils.password import get_decrypted_password

if TYPE_CHECKING:
	from press.press.doctype.server.server import Server


@frappe.whitelist(allow_guest=True)
def service_health():
	"""
	Check if more than 50% of records for each service in the past 5 minutes are failing.
	Returns a dictionary with service names and a boolean, True -> poor health.
	"""
	services_to_check = ["Deploy Candidate Build", "Site Backup"]
	filters = {"creation": ("between", [frappe.utils.add_to_date(minutes=-5), frappe.utils.now()])}
	health_status = {}

	for service in services_to_check:
		total_count = frappe.db.count(service, filters)

		if total_count == 0:
			health_status[service] = False
			continue

		failing_count = frappe.db.count(service, {**filters, "status": "Failure"})

		failure_rate = (failing_count / total_count) * 100
		health_status[service] = failure_rate > 50

	return health_status


"""
DON'T change the method name or path which can affect the api route
If we have to change, please ensure to update mariadb-monitor configurations
"""


@frappe.whitelist(allow_guest=True, methods=["POST"])
def check_db_health(name: str, token: str):
	status = {
		"app_server_healthy": False,
		"db_server_healthy": False,
	}

	if (
		not token
		or not frappe.db.exists("Database Server", name)
		or not (server := frappe.db.exists("Server", {"database_server": name, "status": ("!=", "Archived")}))
		or get_decrypted_password("Server", server, "db_healthcheck_token", raise_exception=False) != token
	):
		# Don't reveal whether the server exists or not or whether the token is valid
		# just return healthy status
		status["app_server_healthy"] = True
		status["db_server_healthy"] = True
		return status

	# Find the app server that is connected to this db server
	app_server = frappe.db.get_value("Server", {"database_server": name})
	if not app_server:
		return status

	app_server_doc: Server = frappe.get_doc("Server", app_server)
	with contextlib.suppress(Exception):
		app_server_doc.ping_agent()
		status["app_server_healthy"] = True

	if status["app_server_healthy"]:
		status["db_server_healthy"] = app_server_doc.ping_mariadb()

	return status
