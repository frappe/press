import frappe
from press.api.server import all as get_all_servers
from press.agent import Agent
from frappe.utils import get_datetime


@frappe.whitelist()
def get_servers(server_filter):
	servers = get_all_servers(server_filter=server_filter)

	for server in servers:
		security_updates_count = frappe.db.count("Security Update", {"server": server.name})
		server["security_updates_status"] = "Up to date"

		if security_updates_count != 0:
			server[
				"security_updates_status"
			] = f"{security_updates_count} security update(s) available"

	return servers


@frappe.whitelist()
def get_security_update_details(update_id):
	return frappe.get_doc("Security Update", update_id).as_dict()


@frappe.whitelist()
def fetch_ssh_sessions(server, start=0, limit=10):
	return frappe.get_all(
		"SSH Session",
		filters={"server": server},
		fields=["name", "user", "datetime"],
		order_by="datetime desc",
		start=start,
		limit=limit,
	)


@frappe.whitelist()
def fetch_ssh_session_logs(server):
	logs_to_display = []
	ssh_logs = Agent(server=server).get("security/ssh_session_logs")

	for log in ssh_logs.get("logs", []):
		if not log["name"].endswith(".timing"):
			log["created_at"] = get_datetime(log["created"]).strftime("%Y-%m-%d %H-%M")

			splited_log = log["name"].split(".")
			log["user"] = splited_log[1]
			log["session_id"] = splited_log[2]

			logs_to_display.append(log)

	return logs_to_display


@frappe.whitelist()
def fetch_ssh_session_activity(server, filename):
	content = Agent(server=server).get(f"security/retrieve_ssh_session_log/{filename}")
	splited_filename = filename.split(".")
	session_user = splited_filename[1]
	session_id = splited_filename[2]

	return {
		"session_user": session_user,
		"session_id": session_id,
		"content": content.get("log_details", "Not Found"),
	}
