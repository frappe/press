# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
import frappe
from tqdm import tqdm

LIMIT_MULTIPLIER = 10
# Increase memory limit. Nothing special about 10,
# Just a number that seems reasonably high to never be reached


def execute():
	servers = frappe.get_all(
		"Server", filters={"status": "Active", "set_bench_memory_limits": True, "public": False}, pluck="name"
	)
	for server in tqdm(servers):
		frappe.db.set_value("Server", server, "set_bench_memory_limits", False)
		benches = frappe.get_all("Bench", filters={"server": server, "status": "Active"}, pluck="name")
		for bench in benches:
			bench = frappe.get_doc("Bench", bench)
			bench.memory_max = LIMIT_MULTIPLIER * bench.memory_max
			bench.memory_swap = LIMIT_MULTIPLIER * bench.memory_swap
			bench.memory_high = LIMIT_MULTIPLIER * bench.memory_high
			bench.save()
		frappe.db.commit()
