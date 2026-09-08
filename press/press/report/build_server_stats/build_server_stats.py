# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import rounded

from press.api.server import prometheus_query

DURATIONS = {
	"5 minutes": 5 * 60,
	"15 minutes": 15 * 60,
	"30 minutes": 30 * 60,
	"1 hour": 60 * 60,
	"3 hours": 3 * 60 * 60,
	"6 hours": 6 * 60 * 60,
	"12 hours": 12 * 60 * 60,
	"24 hours": 24 * 60 * 60,
}
QUEUED = ("Scheduled", "Pending", "Preparing")


def execute(filters=None):
	frappe.only_for("System Manager")
	window = DURATIONS[(filters or {}).get("duration") or "1 hour"]
	return get_columns(), get_data(window), None, get_chart(window)


def get_columns():
	return [
		{
			"fieldname": "server",
			"label": "Server",
			"fieldtype": "Dynamic Link",
			"options": "server_type",
			"width": 250,
		},
		{
			"fieldname": "server_type",
			"label": "Type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 130,
		},
		{"fieldname": "cluster", "label": "Cluster", "fieldtype": "Link", "options": "Cluster", "width": 120},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 90},
		{"fieldname": "iowait", "label": "IO Wait (%)", "fieldtype": "Float", "width": 110},
		{"fieldname": "cpu_used", "label": "CPU Used (%)", "fieldtype": "Float", "width": 110},
		{"fieldname": "memory_used", "label": "Memory Used (%)", "fieldtype": "Float", "width": 130},
		{"fieldname": "disk", "label": "Disk Used (% per mountpoint)", "fieldtype": "Data", "width": 320},
		{"fieldname": "retransmit", "label": "TCP Retransmit (%)", "fieldtype": "Float", "width": 140},
		{"fieldname": "drops", "label": "Dropped Packets/s", "fieldtype": "Float", "width": 140},
		{"fieldname": "receive", "label": "Net In (Mbps)", "fieldtype": "Float", "width": 120},
		{"fieldname": "transmit", "label": "Net Out (Mbps)", "fieldtype": "Float", "width": 120},
		{"fieldname": "builds", "label": "Builds Started", "fieldtype": "Int", "width": 120},
		{"fieldname": "builds_per_hour", "label": "Builds / Hour", "fieldtype": "Float", "width": 120},
		{"fieldname": "running_builds", "label": "Running Builds", "fieldtype": "Int", "width": 120},
		{"fieldname": "queued_builds", "label": "Queued Builds", "fieldtype": "Int", "width": 120},
		{"fieldname": "median_wait", "label": "Median Queue Wait (s)", "fieldtype": "Int", "width": 160},
		{"fieldname": "median_build", "label": "Median Build (s)", "fieldtype": "Int", "width": 140},
		{"fieldname": "p95_build", "label": "P95 Build (s)", "fieldtype": "Int", "width": 130},
		{"fieldname": "median_pull", "label": "Median Image Pull (s)", "fieldtype": "Int", "width": 160},
	]


def get_data(window):
	servers = get_servers()
	names = [server.name for server in servers]
	builds = get_builds(window)
	queue = get_queue()
	pull = get_pull_seconds(window)
	stats = get_fleet_stats(names, window)
	disk = get_fleet_disk_usage(names)
	rows = []
	for server in servers:
		server_builds = builds.get(server.name, [])
		durations = [build.duration for build in server_builds if build.duration is not None]
		waits = [build.wait for build in server_builds if build.wait is not None]
		rows.append(
			{
				"server": server.name,
				"server_type": server.server_type,
				"cluster": server.cluster,
				"status": server.status,
				"disk": disk[server.name],
				"builds": len(server_builds),
				"builds_per_hour": rounded(len(server_builds) / (window / 3600), 1),
				"running_builds": len([build for build in server_builds if build.status == "Running"]),
				"queued_builds": queue.get(server.name, 0),
				"median_wait": percentile(waits, 0.5),
				"median_build": percentile(durations, 0.5),
				"p95_build": percentile(durations, 0.95),
				"median_pull": pull if server.server_type == "Registry Server" else None,
				**{name: rounded(value, 2) for name, value in stats[server.name].items()},
			}
		)
	return rows


def get_servers():
	servers = []
	for server in frappe.get_all(
		"Server", {"status": "Active", "use_for_build": True}, ["name", "cluster", "status"]
	):
		server.server_type = "Server"
		servers.append(server)
	for server in frappe.get_all("Registry Server", {"status": "Active"}, ["name", "status"]):
		server.server_type = "Registry Server"  # no cluster field
		servers.append(server)
	return servers


def get_fleet_stats(servers, window):
	"""CPU, memory and network, averaged over the window, for every server in one query each.

	Loss slows every image push and pull, so the network metrics matter as much as the CPU ones.
	"""
	node = f'job="node", instance=~"{instances(servers)}"'
	interface = f'{node}, device!="lo"'
	memory = f"1 - node_memory_MemAvailable_bytes{{{node}}} / node_memory_MemTotal_bytes{{{node}}}"
	queries = {
		"iowait": f'avg by (instance) (rate(node_cpu_seconds_total{{{node}, mode="iowait"}}[{window}s])) * 100',
		"cpu_used": f'(1 - avg by (instance) (rate(node_cpu_seconds_total{{{node}, mode="idle"}}[{window}s]))) * 100',
		"memory_used": f"avg_over_time(({memory})[{window}s:60s]) * 100",
		"receive": f"sum by (instance) (rate(node_network_receive_bytes_total{{{interface}}}[{window}s]))"
		f" * 8 / (1024 * 1024)",
		"transmit": f"sum by (instance) (rate(node_network_transmit_bytes_total{{{interface}}}[{window}s]))"
		f" * 8 / (1024 * 1024)",
		"retransmit": f"rate(node_netstat_Tcp_RetransSegs{{{node}}}[{window}s])"
		f" / rate(node_netstat_Tcp_OutSegs{{{node}}}[{window}s]) * 100",
		"drops": f"sum by (instance) (rate(node_network_receive_drop_total{{{interface}}}[{window}s])"
		f" + rate(node_network_transmit_drop_total{{{interface}}}[{window}s]))",
	}
	stats = {server: dict.fromkeys(queries, 0) for server in servers}
	for name, query in queries.items():
		for server, value in latest_values(query).items():
			if server in stats:
				stats[server][name] = value
	return stats


def instances(servers):
	"""Prometheus matcher for the whole fleet. Its regexes are anchored, so alternation is safe.

	The dots need two backslashes: PromQL unescapes the string literal before it reads the regex.
	"""
	return "|".join(server.replace(".", r"\\.") for server in servers)


def latest_values(query, key=lambda metric: metric.get("instance")):
	"""Last point of every series, keyed by label. A gap and a NaN both read as zero.

	The window lives inside the query, so ask Prometheus for a short range only. A range as
	long as the window rounds to whole window boundaries and hides the last several minutes.
	"""
	datasets = prometheus_query(query, key, "Asia/Kolkata", 120, 60)["datasets"]
	values = {}
	for dataset in datasets:
		points = [point for point in dataset["values"] if point is not None]
		values[dataset["name"]] = points[-1] if points and points[-1] == points[-1] else 0
	return values


def get_fleet_disk_usage(servers):
	"""Used percent of every real mountpoint, as "/ 41%, /opt/volumes/docker 88%"."""
	filesystem = f'job="node", instance=~"{instances(servers)}", fstype!~"tmpfs|squashfs|overlay|fuse.lxcfs"'
	used = latest_values(
		f"100 * (1 - node_filesystem_avail_bytes{{{filesystem}}}"
		f" / node_filesystem_size_bytes{{{filesystem}}})",
		lambda metric: (metric.get("instance"), metric.get("mountpoint")),
	)
	mountpoints = {server: [] for server in servers}
	for (server, mountpoint), percent in sorted(used.items()):
		if percent and server in mountpoints:
			mountpoints[server].append(f"{mountpoint} {rounded(percent, 1)}%")
	return {server: ", ".join(mounts) for server, mounts in mountpoints.items()}


def percentile(values, fraction):
	"""Nearest rank. Good enough for a handful of builds, and correct at both ends."""
	if not values:
		return 0
	values = sorted(values)
	return values[min(int(len(values) * fraction), len(values) - 1)]


def get_builds(window):
	"""Builds started inside the window, by server, with their queue wait and run time."""
	rows = frappe.db.sql(
		"""
		SELECT
			build_server, status,
			TIMESTAMPDIFF(SECOND, build_start, build_end) AS duration,
			TIMESTAMPDIFF(SECOND, pending_start, build_start) AS wait
		FROM `tabDeploy Candidate Build`
		WHERE build_start >= NOW() - INTERVAL %s SECOND AND build_server IS NOT NULL
		""",
		window,
		as_dict=True,
	)
	builds = {}
	for row in rows:
		builds.setdefault(row.build_server, []).append(row)
	return builds


def get_queue():
	"""Builds waiting for a slot right now. Not bound to the window, a queue is always current."""
	rows = frappe.db.sql(
		"""
		SELECT build_server, COUNT(*) AS queued
		FROM `tabDeploy Candidate Build`
		WHERE status IN %s AND build_server IS NOT NULL
		GROUP BY build_server
		""",
		(QUEUED,),
		as_dict=True,
	)
	return {row.build_server: row.queued for row in rows}


def get_pull_seconds(window):
	"""Median New Bench job. Every one pulls an image, so it tracks how fast the registry serves."""
	rows = frappe.db.sql(
		"""
		SELECT TIMESTAMPDIFF(SECOND, `start`, `end`) AS duration
		FROM `tabAgent Job`
		WHERE job_type = 'New Bench' AND status = 'Success'
			AND `end` >= NOW() - INTERVAL %s SECOND
		""",
		window,
	)
	return percentile([row[0] for row in rows if row[0] is not None], 0.5)


def get_chart(window):
	bucket = max(60, window // 12)  # about twelve bars, whatever the window
	rows = frappe.db.sql(
		"""
		SELECT
			FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(build_start) / %(bucket)s) * %(bucket)s) AS bucket,
			COUNT(*) AS builds
		FROM `tabDeploy Candidate Build`
		WHERE build_start >= NOW() - INTERVAL %(window)s SECOND
		GROUP BY bucket ORDER BY bucket
		""",
		{"bucket": bucket, "window": window},
		as_dict=True,
	)
	return {
		"title": f"Builds started per {bucket // 60} minutes",
		"data": {
			"labels": [row.bucket.strftime("%d %b %H:%M") for row in rows],
			"datasets": [{"name": "Builds", "values": [row.builds for row in rows]}],
		},
		"type": "bar",
	}
