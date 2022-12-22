# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.api.server import usage, total_resource
from frappe.utils import rounded


def execute(filters=None):
	frappe.only_for("System Manager")
	columns = [
		{
			"fieldname": "server",
			"label": frappe._("Server"),
			"fieldtype": "Data",
			"width": 250,
		},
		{
			"fieldname": "cpu",
			"label": frappe._("CPU (%)"),
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"fieldname": "core",
			"label": frappe._("Total Core"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "disk",
			"label": frappe._("Space (%)"),
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"fieldname": "disk_space",
			"label": frappe._("Space (GB)"),
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"fieldname": "memory",
			"label": frappe._("Memory (%)"),
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"fieldname": "total_memory",
			"label": frappe._("Memory (GB)"),
			"fieldtype": "Int",
			"width": 120,
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
				"server": server,
				"cpu": rounded(used_data["vcpu"] * 100, 1),
				"core": available_data["vcpu"],
				"disk": rounded((used_data["disk"] / available_data["disk"]) * 100, 1),
				"disk_space": rounded(available_data["disk"], 2),
				"memory": rounded((used_data["memory"] / available_data["memory"]) * 100, 1),
				"total_memory": rounded(available_data["memory"] / 1024, 2),
			}
		)

	return rows
