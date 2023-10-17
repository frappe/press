# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe


from press.api.server import prometheus_query


def execute(filters=None):
	columns, data = [], []
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
			"width": 200,
		},
		{
			"fieldname": "server_ram",
			"label": frappe._("Server RAM"),
			"fieldtype": "Float",
			"width": 200,
		},
	]

	return columns, data


def get_data(filters):
	bench_workloads = {}
	benches = frappe.get_all(
		"Bench",
		filters={
			"server": "f1-bahrain.frappe.cloud",
			"status": "Active",
			"auto_scale_workers": True,
		},
		pluck="name",
	)
	for bench_name in benches:
		bench = frappe.get_doc("Bench", bench_name)
		bench_workloads[bench_name] = bench.work_load

	total_workload = sum(bench_workloads.values())
	result = []
	for bench in benches:
		result.append(
			{
				"bench": bench,
				"workload": bench_workloads[bench],
				"allocated_ram": 32768 * bench_workloads[bench] / total_workload,
			}
		)

	prometheus_query('sum(avg_over_time(container_memory_rss{name=~".+"}[5m])) by (name)')

	return result
