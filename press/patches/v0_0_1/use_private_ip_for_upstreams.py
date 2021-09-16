# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals

import frappe
from press.agent import Agent
from frappe.utils.fixtures import sync_fixtures


AGENT_GITHUB_ACCESS_TOKEN = ""


def execute():
	settings = frappe.get_single_doc("Press Settings")
	settings.agent_repository_owner = "frappe"

	if not AGENT_GITHUB_ACCESS_TOKEN:
		raise ValueError("GitHub Access Token not found")

	settings.agent_github_access_token = AGENT_GITHUB_ACCESS_TOKEN
	settings.save()

	sync_fixtures("press")

	servers = frappe.get_all("Server", {"is_upstream_setup": True, "status": "Active"})
	for server in servers:
		server = frappe.get_doc("Proxy Server", server.name)
		server.update_agent_ansible()
		agent = Agent(server.proxy_server, "Proxy Server")
		agent.update_upstream_private_ip(server.name)
