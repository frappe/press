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
			"fieldtype": "Link",
			"options": "Server",
			"width": 200,
		},
		{
			"fieldname": "cpu",
			"label": frappe._("vCPUs"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "cpu_used",
			"label": frappe._("CPU Utilization(%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "disk",
			"label": frappe._("Space (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "disk_used",
			"label": frappe._("Space Used(%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "memory",
			"label": frappe._("Memory (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "memory_used",
			"label": frappe._("Memory Used(%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "swap",
			"label": frappe._("Swap (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "swap_used",
			"label": frappe._("Swap Used(%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "memory_required",
			"label": frappe._("Memory Required (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "memory_shortage",
			"label": frappe._("Memory Shortage (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "ram_assigned",
			"label": frappe._("Ram Assigned for Workers (GB)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "new_worker_allocation",
			"label": frappe._("New Worker Allocation"),
			"fieldtype": "Check",
			"width": 100,
		},
	]

	data = get_data()
	return columns, data


def calculate_swap(server):
	query_map = {
		"swap_used": (
			f"""((node_memory_SwapTotal_bytes{{instance="{server}",job="node"}} - node_memory_SwapFree_bytes{{instance="{server}",job="node"}}) / node_memory_SwapTotal_bytes{{instance="{server}",job="node"}}) * 100""",
			lambda x: x,
		),
		"swap": (
			f"""node_memory_SwapTotal_bytes{{instance="{server}",job="node"}} / (1024 * 1024 * 1024)""",
			lambda x: x,
		),
		"required": (
			f"""((node_memory_MemTotal_bytes{{instance="{server}",job="node"}} + node_memory_SwapTotal_bytes{{instance="{server}",job="node"}}) - (node_memory_MemFree_bytes{{instance="{server}",job="node"}} + node_memory_SwapFree_bytes{{instance="{server}",job="node"}} + node_memory_Cached_bytes{{instance="{server}",job="node"}} + node_memory_Buffers_bytes{{instance="{server}",job="node"}} + node_memory_SwapCached_bytes{{instance="{server}",job="node"}})) / (1024 * 1024 * 1024)""",
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
	servers = frappe.get_all(
		"Server", dict(status="Active"), pluck="name"
	) + frappe.get_all("Database Server", dict(status="Active"), pluck="name")

	rows = []
	for server in servers:
		used_data = usage(server)
		available_data = total_resource(server)
		swap_memory = calculate_swap(server)

		rows.append(
			{
				"server": server,
				"cpu": available_data.get("vcpu", 0),
				"cpu_used": rounded(used_data.get("vcpu", 0) * 100, 1),
				"disk": rounded(available_data.get("disk", 0), 2),
				"disk_used": rounded(
					(used_data.get("disk", 0) / available_data.get("disk", 1)) * 100, 1
				),
				"memory": rounded(available_data.get("memory", 0) / 1024, 2),
				"memory_used": rounded(
					(used_data.get("memory", 0) / available_data.get("memory", 1)) * 100, 1
				),
				"swap": rounded(swap_memory.get("swap", 0), 1),
				"swap_used": rounded(swap_memory.get("swap_used", 0), 1),
				"memory_required": rounded(swap_memory.get("required", 0), 1),
				"memory_shortage": max(
					rounded(swap_memory.get("required", 0), 1)
					- rounded(available_data.get("memory", 0) / 1024, 2),
					0,
				),
				"new_worker_allocation": frappe.db.get_value(
					"Server", server, "new_worker_allocation"
				),
				"ram_assigned": (frappe.db.get_value("Server", server, "ram") or 0) / 1024,
			}
		)

	return rows
