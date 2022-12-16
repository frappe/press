# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.api.server import usage, total_resource


def execute(filters=None):
	frappe.only_for("System Manager")
	columns = [
		{
			"fieldname": "server",
			"label": frappe._("Server"),
			"fieldtype": "Float",
			"width": 70,
		},
		{
			"fieldname": "cpu",
			"label": frappe._("CPU"),
			"fieldtype": "Float",
			"width": 70,
		},
		{
			"fieldname": "disk",
			"label": frappe._("Space"),
			"fieldtype": "Float",
			"width": 70,
		},
		{
			"fieldname": "memory",
			"label": frappe._("Memory"),
			"fieldtype": "Float",
			"width": 70,
		},
	]

	data = get_data()
	return columns, data


def get_data():
	servers = frappe.get_all("Server", dict(status="Active"), pluck="name")

	rows = []
	for server in servers:
		used_data = usage(server)
		available_data = total_resource(server)

		rows.append(
			{
				"cpu": (used_data["vcpu"] / available_data["datasets"][0]["values"][-1]) * 100,
				"disk": (used_data["disk"] / available_data["datasets"][0]["values"][-1]) * 100,
				"memory": (used_data["memory"] / available_data["datasets"][0]["values"][-1]) * 100,
			}
		)

	return rows
