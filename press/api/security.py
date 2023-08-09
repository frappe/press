import frappe
from press.api.server import all as get_all_servers


@frappe.whitelist()
def get_servers(server_filter="All Servers"):
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
def fetch_security_updates(server, start=0, limit=10):
	return frappe.get_all(
		"Security Update",
		filters={"server": server},
		fields=["name", "package", "version", "priority", "priority_level", "datetime"],
		order_by="priority_level asc",
		start=start,
		limit=limit,
	)


@frappe.whitelist()
def get_security_update_details(update_id):
	return frappe.get_doc("Security Update", update_id).as_dict()
