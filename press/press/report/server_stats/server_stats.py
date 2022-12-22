# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.api.server import usage, total_resource, prometheus_query
from frappe.utils import rounded


def execute(filters=None):
	frappe.only_for("System Manager")
	columns = [
		{
			"fieldname": "server",
			"label": frappe._("Server"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "cpu",
			"label": frappe._("CPU (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "core",
			"label": frappe._("Total Core"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "disk",
			"label": frappe._("Space (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "disk_space",
			"label": frappe._("Space (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "memory",
			"label": frappe._("Memory (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "total_memory",
			"label": frappe._("Memory (GB)"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "swap",
			"label": frappe._("Swap (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
	]

	data = get_data()
	return columns, data


def calculate_swap(server):
	query_map = {
		"swap": (
			f"""((node_memory_SwapTotal_bytes{{instance="{server}",job="node"}} - node_memory_SwapFree_bytes{{instance="{server}",job="node"}}) / (node_memory_SwapTotal_bytes{{instance="{server}",job="node"}} )) * 100""",
			lambda x: x,
		),
	}

	result = {}
	for usage_type, query in query_map.items():
		response = prometheus_query(query[0], query[1], "Asia/Kolkata", 120, 120)["datasets"]
		if response:
			result[usage_type] = response[0]["values"][-1]
	return result


def get_data():
	servers = frappe.get_all("Server", dict(status="Active"), pluck="name")

	rows = []
	for server in servers:
		used_data = usage(server)
		available_data = total_resource(server)
		swap_memory = calculate_swap(server)

		rows.append(
			{
				"server": server,
				"cpu": rounded(used_data["vcpu"] * 100, 1),
				"core": available_data["vcpu"],
				"disk": rounded((used_data["disk"] / available_data["disk"]) * 100, 1),
				"disk_space": rounded(available_data["disk"], 2),
				"memory": rounded((used_data["memory"] / available_data["memory"]) * 100, 1),
				"total_memory": rounded(available_data["memory"] / 1024, 2),
				"swap": rounded(swap_memory["swap"], 1),
			}
		)

	return rows
