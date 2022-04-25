# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe
from itertools import groupby
from press.utils import log_error


@frappe.whitelist(allow_guest=True)
def targets(token):
	monitor_token = frappe.db.get_single_value("Press Settings", "monitor_token")
	if token != monitor_token:
		return

	sites = frappe.get_all(
		"Site", ["name", "bench"], {"status": "Active"}, order_by="bench, name"
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
		"proxy": ["node", "nginx", "proxysql"],
		"app": ["node", "nginx", "docker", "cadvisor", "gunicorn"],
		"database": ["node", "mariadb"],
	}
	for cluster in clusters:
		cluster["jobs"] = {}

		for server_type, server_type_servers in servers.items():
			for server in server_type_servers:
				if server.cluster == cluster.name:
					for job in job_map[server_type]:
						cluster["jobs"].setdefault(job, []).append(server.name)

	domains = frappe.get_all(
		"Site Domain", ["name", "site"], {"dns_type": "CNAME"}, order_by="name"
	)

	tls = []
	server_types = [
		"Server",
		"Proxy Server",
		"Database Server",
		"Registry Server",
		"Log Server",
		"Monitor Server",
		"Analytics Server",
	]
	for server_type in server_types:
		tls += frappe.get_all(server_type, {"status": ("!=", "Archived")}, ["name"])

	return {"benches": benches, "clusters": clusters, "domains": domains, "tls": tls}


@frappe.whitelist(allow_guest=True, xss_safe=True)
def alert(*args, **kwargs):
	try:
		user = frappe.session.user
		frappe.set_user("Administrator")

		doc = frappe.get_doc(
			{
				"doctype": "Alertmanager Webhook Log",
				"payload": frappe.request.get_data().decode(),
			}
		)
		doc.insert()
	except Exception:
		log_error("Alertmanager Webhook Error", args=args, kwargs=kwargs)
		raise Exception
	finally:
		frappe.set_user(user)
