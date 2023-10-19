# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe


from press.api.server import prometheus_query


def execute(filters=None):
	columns = [
		{
			"fieldname": "bench",
			"label": frappe._("Bench"),
			"fieldtype": "Link",
			"options": "Bench",
			"width": 200,
		},
		{
			"fieldname": "workload",
			"label": frappe._("Workload"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "allocated_ram",
			"label": frappe._("Allocated RAM"),
			"fieldtype": "Float",
			"width": 200,
		},
		{
			"fieldname": "server_ram",
			"label": frappe._("Server RAM"),
			"fieldtype": "Float",
			"width": 200,
		},
	]

	return columns, get_data(filters)


def get_data(filters):
	server_name = filters.get("server").replace("%", "")  # hack to bypass weird sentry bug
	benches = frappe.get_all(
		"Bench",
		filters={
			"server": server_name,
			"status": "Active",
			"auto_scale_workers": True,
		},
		pluck="name",
	)
	server = frappe.get_doc("Server", server_name)
	result = []
	for bench_name in benches:
		bench = frappe.get_doc("Bench", bench_name)

		gn, bg = bench.allocate_workers(
			server.workload, server.max_gunicorn_workers, server.max_bg_workers
		)
		result.append(
			{
				"bench": bench_name,
				"workload": bench.workload,
				"allocated_ram": gn * 150 + bg * (3 * 80),
			}
		)

	prom_res = prometheus_query(
		f'sum(avg_over_time(container_memory_rss{{instance="{server_name}", name=~".+"}}[5m])) by (name)',
		lambda x: x,
		"Asia/Kolkata",
		60,
		60,
	)["datasets"]
	for row in result:
		for prom_row in prom_res:
			if row["bench"] == prom_row["name"]["name"]:
				row["server_ram"] = prom_row["values"][-1] / 1024 / 1024
				break

	return result
