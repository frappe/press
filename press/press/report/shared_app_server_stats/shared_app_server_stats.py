# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.api.server import usage, total_resource, prometheus_query, calculate_swap
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
			"fieldname": "disk_free",
			"label": frappe._("Space Free (GB)"),
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
		{
			"fieldname": "load_1",
			"label": frappe._("Load Average 1 (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "load_5",
			"label": frappe._("Load Average 5 (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "load_15",
			"label": frappe._("Load Average 15 (%)"),
			"fieldtype": "Float",
			"width": 100,
		},
	]

	data = get_data()
	return columns, data


def calculate_load(server):
	query_map = {
		"load_1": (
			f"""avg(node_load1{{instance="{server}", job="node"}}) / count(count(node_cpu_seconds_total{{instance="{server}", job="node"}}) by (cpu)) * 100""",
			lambda x: x,
		),
		"load_5": (
			f"""avg(node_load5{{instance="{server}", job="node"}}) / count(count(node_cpu_seconds_total{{instance="{server}", job="node"}}) by (cpu)) * 100""",
			lambda x: x,
		),
		"load_15": (
			f"""avg(node_load15{{instance="{server}", job="node"}}) / count(count(node_cpu_seconds_total{{instance="{server}", job="node"}}) by (cpu)) * 100""",
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
	servers = frappe.db.sql_list(
		"""
		select
		  server.name
		from
		  tabServer server
		where
		  (
			server.team like "%%erpnext.com"
			or server.team = ""
		  )
		  and server.provider = "AWS EC2"
		  and status = "Active"
		"""
	)

	rows = []
	for server in servers:
		used_data = usage(server)
		available_data = total_resource(server)
		swap_memory = calculate_swap(server)
		load = calculate_load(server)

		rows.append(
			{
				"server": server,
				"cpu": available_data.get("vcpu", 0),
				"cpu_used": rounded(used_data.get("vcpu", 0) * 100, 1),
				"disk": rounded(available_data.get("disk", 0), 2),
				"disk_used": rounded(
					(used_data.get("disk", 0) / available_data.get("disk", 1)) * 100, 1
				),
				"disk_free": available_data.get("disk", 0) - used_data.get("disk", 0),
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
				"load_1": rounded(load.get("load_1", 0), 1),
				"load_5": rounded(load.get("load_5", 0), 1),
				"load_15": rounded(load.get("load_15", 0), 1),
			}
		)

	return rows
