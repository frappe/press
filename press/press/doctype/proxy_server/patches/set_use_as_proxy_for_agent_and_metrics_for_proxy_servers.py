import frappe


def execute():
	for cluster in frappe.get_all("Cluster"):
		if not frappe.db.get_value(
			"Proxy Server",
			{"status": "Active", "cluster": cluster.name, "use_as_proxy_for_agent_and_metrics": 1},
		):
			frappe.db.set_value(
				"Proxy Server",
				frappe.db.get_value("Proxy Server", {"status": "Active", "cluster": cluster.name}),
				"use_as_proxy_for_agent_and_metrics",
				1,
			)
