# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


from itertools import groupby

import frappe
from frappe.rate_limiter import rate_limit

from press.exceptions import AlertRuleNotEnabled
from press.press.doctype.monitor_server.monitor_server import get_monitor_server_ips
from press.utils import log_error, servers_using_alternative_port_for_communication


def get_benches():
	self_hosted_stand_alone_servers = frappe.get_all(
		"Server",
		{"is_standalone": True, "is_self_hosted": True, "status": "Active"},
		pluck="name",
	)
	monitoring_disabled_servers = frappe.get_all(
		"Server", {"is_monitoring_disabled": True, "status": ("!=", "Archived")}, pluck="name"
	)
	excluded_servers = set(self_hosted_stand_alone_servers + monitoring_disabled_servers)
	sites = frappe.get_all(
		"Site",
		["name", "bench"],
		{"status": "Active", "server": ("not in", excluded_servers), "is_monitoring_disabled": False},
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


def get_clusters():  # noqa: C901
	servers = {}
	servers["proxy"] = frappe.get_all(
		"Proxy Server",
		{"status": ("!=", "Archived")},
		["name", "cluster", "use_as_proxy_for_agent_and_metrics", "ip"],
	)
	servers["app"] = frappe.get_all(
		"Server",
		{"status": ("!=", "Archived"), "is_monitoring_disabled": False},
		["name", "cluster", "ip", "private_ip"],
	)
	servers["database"] = frappe.get_all(
		"Database Server",
		{"status": ("!=", "Archived"), "is_monitoring_disabled": False},
		["name", "cluster", "ip", "private_ip"],
	)
	servers["nfs"] = frappe.get_all(
		"NFS Server", {"status": ("!=", "Archived")}, ["name", "cluster", "ip", "private_ip"]
	)
	servers["nat"] = frappe.get_all("NAT Server", {"status": ("!=", "Archived")}, ["name", "cluster", "ip"])

	proxy_servers_by_clusters = groupby(servers["proxy"], lambda x: x.cluster)

	clusters = frappe.get_all("Cluster")
	job_map = get_job_map()
	servers_using_alternative_port = servers_using_alternative_port_for_communication()
	for cluster in clusters:
		cluster["jobs"] = {}

		for server_type, server_type_servers in servers.items():
			for server in server_type_servers:
				if server.cluster == cluster.name:
					for job in job_map[server_type]:
						_server = (
							f"{server.name}:8443"
							if server.name in servers_using_alternative_port
							else server.name
						)

						if server.ip:
							cluster["jobs"].setdefault(job, []).append(_server)
						elif server.private_ip:
							proxies = proxy_servers_by_clusters[cluster.name]
							relevant_proxy_server = [
								p for p in proxies if p.use_as_proxy_for_agent_and_metrics
							]
							if relevant_proxy_server:
								proxy_server = (
									f"{relevant_proxy_server[0].name}:8443"
									if relevant_proxy_server[0].name in servers_using_alternative_port
									else relevant_proxy_server[0].name
								)
								cluster["jobs"]["proxied"].setdefault(job, []).append(
									{"proxy": proxy_server, "server": _server}
								)

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
		"NFS Server",
		"NAT Server",
	]
	for server_type in server_types:
		filters = {"status": ("!=", "Archived")}
		if server_type in ("Server", "Database Server"):
			filters["is_monitoring_disabled"] = False
			filters["is_for_recovery"] = False
		tls += frappe.get_all(server_type, filters, ["name"])

	return tls


def get_targets_method_rate_limit() -> int:
	if (
		frappe.local
		and hasattr(frappe.local, "request_ip")
		and frappe.local.request_ip in get_monitor_server_ips()
	):
		# Allow no limit for known monitor servers
		return 1000

	# For unknown IPs, allow only 2 request per minute
	return 2


MONITORING_ENDPOINT_RATE_LIMIT_WINDOW_SECONDS = 60


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=get_targets_method_rate_limit, seconds=MONITORING_ENDPOINT_RATE_LIMIT_WINDOW_SECONDS)
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
		webhook_token = frappe.db.get_value(
			"Monitor Server",
			frappe.db.get_single_value("Press Settings", "monitor_server", cache=True),
			"webhook_token",
			cache=True,
		)

		if frappe.request.args.get("webhook_token") != webhook_token:
			raise frappe.AuthenticationError("Invalid credentials")

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


def get_job_map() -> dict[str, list[str]]:
	DEFAULT_JOB_MAP = {
		"proxy": ["node", "nginx", "proxysql", "mariadb_proxy"],
		"app": ["node", "nginx", "docker", "cadvisor", "gunicorn", "rq"],
		"nfs": ["node", "nginx", "docker", "cadvisor", "gunicorn", "rq"],
		"database": ["node", "mariadb"],
		"nat": ["node"],
	}

	if frappe.local and hasattr(frappe.local, "request_ip"):
		if frappe.get_value(
			"Monitor Server",
			{"ip": frappe.local.request_ip, "status": ("!=", "Archived")},
			"only_monitor_uptime_metrics",
			cache=True,
		):
			return {
				"proxy": ["node"],
				"app": ["node"],
				"nfs": ["node"],
				"database": ["node"],
				"nat": ["node"],
			}
		return DEFAULT_JOB_MAP
	return DEFAULT_JOB_MAP
