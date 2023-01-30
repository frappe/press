# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from press.agent import Agent
from press.press.report.server_stats.server_stats import get_servers


def execute(filters=None):
	frappe.only_for("System Manager")
	columns = [
		{
			"fieldname": "server",
			"label": frappe._("Server"),
			"fieldtype": "Dynamic Link",
			"options": "server_type",
			"width": 200,
		},
		{
			"fieldname": "server_type",
			"label": frappe._("Server Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 140,
		},
		{
			"fieldname": "commit",
			"label": frappe._("Commit"),
			"fieldtype": "Data",
			"width": 360,
		},
		{
			"fieldname": "status",
			"label": frappe._("Status"),
			"fieldtype": "Long Text",
			"width": 100,
		},
		{
			"fieldname": "upstream",
			"label": frappe._("Upstream"),
			"fieldtype": "Data",
			"width": 260,
		},
		{
			"fieldname": "show",
			"label": frappe._("Show"),
			"fieldtype": "Long Text",
			"width": 100,
		},
	]

	data = get_data(filters)
	return columns, data


def get_data(filters):
	rows = []
	for server in get_servers(filters):
		try:
			version = Agent(server.name, server.server_type).get_version()
			if version is None:
				version = {}
		except Exception:
			version = {}
		rows.append(
			{
				"server": server.name,
				"server_type": server.server_type,
				**version,
			}
		)
	return rows


@frappe.whitelist()
def update_agent(filters):
	frappe.only_for("System Manager")
	for server in get_servers(frappe._dict(json.loads(filters))):
		server = frappe.get_doc(server.server_type, server.name)
		server.update_agent_ansible()
