# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from press.agent import Agent
from frappe.utils.fixtures import sync_fixtures


def execute():
	settings = frappe.get_doc("Press Settings", "Press Settings")
	settings.agent_repository_owner = "frappe"

	settings.agent_github_access_token = input("GitHub Access Token: ")
	settings.save()

	sync_fixtures("press")

	servers = frappe.get_all(
		"Server", {"is_upstream_setup": True, "status": "Active"}, ["name", "proxy_server"]
	)
	for server in servers:
		proxy_server = frappe.get_doc("Proxy Server", server.proxy_server)
		proxy_server.update_agent_ansible()

		agent = Agent(server.proxy_server, "Proxy Server")
		agent.update_upstream_private_ip(server.name)
