# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from itertools import groupby


@frappe.whitelist(allow_guest=True)
def targets(token):
	monitor_token = frappe.db.get_single_value("Press Settings", "monitor_token")
	if token != monitor_token:
		return

	sites = frappe.get_all(
		"Site",
		["name", "bench"],
		{"status": ("not in", ("Archived", "Suspended", "Inactive"))},
		order_by="bench, name",
	)

	benches = []
	for bench_name, sites in groupby(sites, lambda x: x.bench):
		bench = frappe.db.get_value(
			"Bench", bench_name, ["name", "cluster", "server", "group"], as_dict=True
		)
		bench.update({"sites": [site.name for site in sites]})
		benches.append(bench)

	servers = {}
	servers["proxy"] = frappe.get_all(
		"Proxy Server", {"status": ("!=", "Archived")}, ["name", "cluster"]
	)
	servers["app"] = frappe.get_all(
		"Server", {"status": ("!=", "Archived")}, ["name", "cluster"]
	)
	servers["database"] = frappe.get_all(
		"Database Server", {"status": ("!=", "Archived")}, ["name", "cluster"]
	)
	clusters = frappe.get_all("Cluster")
	job_map = {
		"proxy": ["node", "nginx"],
		"app": ["node", "nginx", "docker", "cadvisor", "gunicorn"],
		"database": ["node", "mariadb"],
	}
	for cluster in clusters:
		cluster["jobs"] = {}

	for server_type, servers in servers.items():
		for server in servers:
			for job in job_map[server_type]:
				cluster["jobs"].setdefault(job, []).append(server.name)

	return {"benches": benches, "clusters": clusters}
