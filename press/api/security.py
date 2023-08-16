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
def fetch_security_updates(
	filters=None, order_by=None, limit_start=None, limit_page_length=None
):
	return frappe.get_all(
		"Security Update",
		filters=filters,
		fields=["name", "package", "version", "priority", "priority_level", "datetime"],
		order_by=order_by or "priority_level asc",
		start=limit_start,
		limit=limit_page_length,
	)


@frappe.whitelist()
def get_security_update_details(update_id):
	return frappe.get_doc("Security Update", update_id).as_dict()


@frappe.whitelist()
def fetch_ssh_sessions_from_db(server):
	return frappe.get_all(
		"SSH Session Log",
		filters={"server": server},
		fields=[
			"name",
			"ssh_user as user",
			"created_at",
			"session_id",
			"filename",
		],
		order_by="created_at desc",
	)


@frappe.whitelist()
def fetch_ssh_session_logs(server, server_type):
	from press.press.doctype.ssh_session_log.ssh_session_log import SSHSessionLog

	logs_to_display = []
	ssh_logs = Agent(server=server).get("security/ssh_session_logs")

	for log in ssh_logs.get("logs", []):
		if not log["name"].endswith(".timing"):
			log["created_at"] = get_datetime(log["created"]).strftime("%Y-%m-%d %H:%M")

			splited_log = log["name"].split(".")
			log["user"] = splited_log[1]
			log["session_id"] = splited_log[2]

			logs_to_display.append(log)

			SSHSessionLog.create_ssh_session_log(log, server, server_type)

	return logs_to_display


@frappe.whitelist()
def fetch_ssh_session_activity(server, filename):
	from press.press.doctype.ssh_session_log.ssh_session_log import (
		SSHSessionLog,
		get_activity_log_from_db,
	)

	if not filename or not server:
		return {}

	log = get_activity_log_from_db(filename)

	if log:
		return log

	content = Agent(server=server).get(f"security/retrieve_ssh_session_log/{filename}")
	splited_filename = filename.split(".")
	session_user = splited_filename[1]
	session_id = splited_filename[2]

	try:
		SSHSessionLog.update_ssh_session_log(filename, content.get("log_details"))
	except frappe.DoesNotExistError:
		pass
	except Exception:
		pass

	return {
		"session_user": session_user,
		"session_id": session_id,
		"content": content.get("log_details", "Not Found"),
	}


@frappe.whitelist()
def get_firewall_rules(server, server_type):
	from press.press.doctype.firewall_rule.firewall_rule import FirewallRule

	return FirewallRule.fetch_firewall_rules(server, server_type)
