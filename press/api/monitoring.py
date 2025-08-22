# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


from itertools import groupby

import frappe
from frappe.rate_limiter import rate_limit

from press.exceptions import AlertRuleNotEnabled
from press.utils import log_error, servers_using_alternative_port_for_communication


def get_benches():
	self_hosted_stand_alone_servers = frappe.get_all(
		"Server",
		{"is_standalone": True, "is_self_hosted": True, "status": "Active"},
		pluck="name",
	)
	sites = frappe.get_all(
		"Site",
		["name", "bench"],
		{"status": "Active", "server": ("not in", self_hosted_stand_alone_servers)},
		ignore_ifnull=True,
	)
	sites.sort(key=lambda x: (x.bench, x.name))

	bench_map = {
		bench.name: bench
		for bench in frappe.get_all(
			"Bench",
			{"name": ("in", set(site.bench for site in sites))},
			["name", "cluster", "server", "group"],
			ignore_ifnull=True,
		)
	}
	benches = []
	for bench_name, _sites in groupby(sites, lambda x: x.bench):
		bench = bench_map[bench_name]
		bench.update({"sites": [site.name for site in _sites]})
		benches.append(bench)

	return benches


def get_clusters():
	servers = {}
	servers["proxy"] = frappe.get_all("Proxy Server", {"status": ("!=", "Archived")}, ["name", "cluster"])
	servers["app"] = frappe.get_all("Server", {"status": ("!=", "Archived")}, ["name", "cluster"])
	servers["database"] = frappe.get_all(
		"Database Server", {"status": ("!=", "Archived")}, ["name", "cluster"]
	)
	clusters = frappe.get_all("Cluster")
	job_map = {
		"proxy": ["node", "nginx", "proxysql", "mariadb_proxy"],
		"app": ["node", "nginx", "docker", "cadvisor", "gunicorn", "rq"],
		"database": ["node", "mariadb"],
	}
	servers_using_alternative_port = servers_using_alternative_port_for_communication()
	for cluster in clusters:
		cluster["jobs"] = {}

		for server_type, server_type_servers in servers.items():
			for server in server_type_servers:
				if server.cluster == cluster.name:
					for job in job_map[server_type]:
						if server.name in servers_using_alternative_port:
							cluster["jobs"].setdefault(job, []).append(f"{server.name}:8443")
						else:
							cluster["jobs"].setdefault(job, []).append(server.name)

	return clusters


def get_domains():
	return frappe.get_all(
		"Site Domain", ["name", "site"], {"tls_certificate": ("is", "set")}, order_by="name"
	)


def get_tls():
	tls = []
	server_types = [
		"Server",
		"Proxy Server",
		"Database Server",
		"Registry Server",
		"Log Server",
		"Monitor Server",
		"Analytics Server",
		"Trace Server",
	]
	for server_type in server_types:
		tls += frappe.get_all(server_type, {"status": ("!=", "Archived")}, ["name"])

	return tls


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def targets(token=None):
	if not token:
		frappe.throw_permission_error()
	monitor_token = frappe.db.get_single_value("Press Settings", "monitor_token", cache=True)
	if token != monitor_token:
		return None

	return {"benches": get_benches(), "clusters": get_clusters(), "domains": get_domains(), "tls": get_tls()}


@frappe.whitelist(allow_guest=True, xss_safe=True)
def alert(*args, **kwargs):
	user = frappe.session.user
	try:
		monitor_token = frappe.db.get_single_value("Press Settings", "monitor_token", cache=True)

		if frappe.request.args.get("monitor_token") != monitor_token:
			raise frappe.AuthenticationError("Invalid credentials")

		monitor_token = frappe.db.get_single_value("Press Settings", "monitor_token", cache=True)

		if frappe.request.args.get("monitor_token") != monitor_token:
			raise Exception

		frappe.set_user("Administrator")

		doc = frappe.get_doc(
			{
				"doctype": "Alertmanager Webhook Log",
				"payload": frappe.request.get_data().decode(),
			}
		)
		doc.insert()
	except AlertRuleNotEnabled:
		pass

	except frappe.AuthenticationError:
		log_error("Alertmanager Webhook Authentication Error", args=args, kwargs=kwargs)

	except Exception:
		log_error("Alertmanager Webhook Error", args=args, kwargs=kwargs)
		raise

	finally:
		frappe.set_user(user)
