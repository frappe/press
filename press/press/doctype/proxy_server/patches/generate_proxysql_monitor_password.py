import frappe


def execute():
	frappe.reload_doc("press", "doctype", "proxy_server")

	for server in frappe.get_all(
		"Proxy Server", filters={"status": "Active"}, pluck="name"
	):
		server = frappe.get_doc("Proxy Server", server)
		server.proxysql_monitor_password = frappe.generate_hash()
		server.save()
