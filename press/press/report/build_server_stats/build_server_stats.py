# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from collections import Counter
from datetime import datetime

import frappe
from frappe.utils import add_to_date, rounded

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
QUEUED = ("Scheduled", "Pending")
# Preparing already holds the build server, so it counts against capacity like Running does
RUNNING = ("Preparing", "Running")


def execute(filters=None):
	frappe.only_for("System Manager")
	window = DURATIONS[(filters or {}).get("duration") or "1 hour"]
	builds = get_builds(window)
	return get_columns(), get_data(window, builds), get_cluster_loss(window), get_chart(window, builds)


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


def get_data(window, builds):
	servers = get_servers()
	names = [server.name for server in servers]
	builds_by_server = group_by_server(builds)
	active = get_active_builds()
	pull = get_pull_seconds(window)
	stats = get_fleet_stats(names, window)
	disk = get_fleet_disk_usage(names)
	rows = []
	for server in servers:
		server_builds = builds_by_server.get(server.name, [])
		durations = seconds_of(server_builds, "build_start", "build_end")
		waits = seconds_of(server_builds, "pending_start", "build_start")
		rows.append(
			{
				"server": server.name,
				"server_type": server.server_type,
				"cluster": server.cluster,
				"status": server.status,
				"disk": disk[server.name],
				"builds": len(server_builds),
				"builds_per_hour": rounded(len(server_builds) / (window / 3600), 1),
				"running_builds": active.get(server.name, {}).get("running", 0),
				"queued_builds": active.get(server.name, {}).get("queued", 0),
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
	"""Builds that started inside the window."""
	return frappe.get_all(
		"Deploy Candidate Build",
		{
			"build_start": (">=", add_to_date(None, seconds=-window)),
			"build_server": ("is", "set"),
		},
		["build_server", "status", "pending_start", "build_start", "build_end"],
	)


def group_by_server(builds):
	grouped = {}
	for build in builds:
		grouped.setdefault(build.build_server, []).append(build)
	return grouped


def seconds_of(builds, start_field, end_field):
	"""Seconds between two stamps of each build. A build that lacks either stamp drops out."""
	spans = []
	for build in builds:
		if build.get(start_field) and build.get(end_field):
			spans.append((build.get(end_field) - build.get(start_field)).total_seconds())
	return spans


def get_active_builds():
	"""Builds holding or waiting for a server right now.

	Never bound to the window. A build that started before the window, or one still preparing,
	uses the server all the same, and an operator who reads this column wants the true load.
	"""
	builds = frappe.get_all(
		"Deploy Candidate Build",
		{"status": ("in", QUEUED + RUNNING), "build_server": ("is", "set")},
		["build_server", "status"],
	)
	active = {}
	for build in builds:
		counts = active.setdefault(build.build_server, {"queued": 0, "running": 0})
		counts["queued" if build.status in QUEUED else "running"] += 1
	return active


def get_pull_seconds(window):
	"""Median New Bench job. Every one pulls an image, so it tracks how fast the registry serves."""
	jobs = frappe.get_all(
		"Agent Job",
		{
			"job_type": "New Bench",
			"status": "Success",
			"end": (">=", add_to_date(None, seconds=-window)),
		},
		["start", "end"],
	)
	return percentile(seconds_of(jobs, "start", "end"), 0.5)


def get_chart(window, builds):
	bucket = max(60, window // 12)  # about twelve bars, whatever the window
	counts = Counter(floor_to_bucket(build.build_start, bucket) for build in builds)
	labels = sorted(counts)
	return {
		"title": f"Builds started per {bucket // 60} minutes",
		"data": {
			"labels": [label.strftime("%d %b %H:%M") for label in labels],
			"datasets": [{"name": "Builds", "values": [counts[label] for label in labels]}],
		},
		"type": "bar",
	}


def floor_to_bucket(moment, bucket):
	return datetime.fromtimestamp(moment.timestamp() // bucket * bucket)


def get_cluster_loss(window):
	"""Packet loss per cluster, above the table. A bad region shows here before a server does."""
	retransmit = latest_values(
		f'avg by (cluster) (rate(node_netstat_Tcp_RetransSegs{{job="node"}}[{window}s])'
		f' / rate(node_netstat_Tcp_OutSegs{{job="node"}}[{window}s])) * 100',
		lambda metric: metric.get("cluster") or "No cluster",
	)
	drops = latest_values(
		f'sum by (cluster) (rate(node_network_receive_drop_total{{job="node", device!="lo"}}[{window}s])'
		f' + rate(node_network_transmit_drop_total{{job="node", device!="lo"}}[{window}s]))',
		lambda metric: metric.get("cluster") or "No cluster",
	)
	rows = []
	for cluster in sorted(retransmit.keys() | drops.keys(), key=lambda name: -retransmit.get(name, 0)):
		rows.append(cluster_loss_row(cluster, retransmit.get(cluster, 0), drops.get(cluster, 0)))
	if not rows:
		return None
	return (
		"<b>Packet loss per cluster</b>"
		"<table class='table table-bordered'><thead><tr>"
		"<th>Cluster</th><th>TCP Retransmit (%)</th><th>Dropped Packets/s</th>"
		"</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
	)


def cluster_loss_row(cluster, retransmit, drops):
	red = "style='color: var(--red-600); font-weight: 600'" if retransmit >= 1 or drops > 0 else ""
	return (
		f"<tr {red}><td>{frappe.utils.escape_html(cluster)}</td>"
		f"<td>{rounded(retransmit, 2)}</td><td>{rounded(drops, 2)}</td></tr>"
	)
