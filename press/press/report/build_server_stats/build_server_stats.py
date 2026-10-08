# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe.query_builder.functions import Coalesce
from frappe.utils import add_to_date, get_datetime, get_system_timezone, now_datetime, rounded

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
	"3 days": 3 * 24 * 60 * 60,
	"7 days": 7 * 24 * 60 * 60,
	"15 days": 15 * 24 * 60 * 60,
}
QUEUED = ("Scheduled", "Pending")
# Preparing already holds the build server, so it counts against capacity like Running does
RUNNING = ("Preparing", "Running")
VOLUMES = "/opt/volumes/"


@dataclass
class Period:
	start: datetime
	end: datetime

	@property
	def seconds(self):
		return int((self.end - self.start).total_seconds())


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = frappe._dict(filters or {})
	period = get_period(filters)
	builds = get_builds(period)
	servers = get_servers()
	disk = DiskUsage([server.name for server in servers], period.end)
	return (
		get_columns(disk),
		get_data(period, builds, servers, disk),
		get_cluster_loss(period),
		get_selected_chart(filters.chart, period, builds, servers),
	)


def get_period(filters):
	"""From and To win over Duration. Without a From, Duration counts back from To, or from now."""
	end = get_datetime(filters.to_datetime or now_datetime())
	start = get_datetime(
		filters.from_datetime or add_to_date(end, seconds=-DURATIONS[filters.duration or "1 hour"])
	)
	# A shorter period holds fewer than two scrapes, so every rate reads zero
	if (end - start).total_seconds() < DURATIONS["5 minutes"]:
		frappe.throw(
			"The period must be at least 5 minutes long. Choose a From at least 5 minutes before To."
		)
	return Period(start, end)


def get_columns(disk):
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
		{"fieldname": "iowait", "label": "IO Wait (%)", "fieldtype": "Float", "width": 110},
		{"fieldname": "cpu_used", "label": "CPU Used (%)", "fieldtype": "Float", "width": 110},
		{"fieldname": "memory_used", "label": "Memory Used (%)", "fieldtype": "Float", "width": 130},
		*disk.columns(),
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
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 90},
	]


def get_data(period, builds, servers, disk):
	names = [server.name for server in servers]
	builds_by_server = group_by_server(builds)
	active = get_active_builds()
	pull = get_pull_seconds(period)
	stats = get_fleet_stats(names, period)
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
				**disk.cells(server.name),
				"builds": len(server_builds),
				"builds_per_hour": rounded(len(server_builds) / (period.seconds / 3600), 1),
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


def get_fleet_stats(servers, period):
	"""CPU, memory and network, averaged over the period, for every server in one query each.

	Loss slows every image push and pull, so the network metrics matter as much as the CPU ones.
	"""
	window = period.seconds
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
		for server, value in latest_values(query, period.end).items():
			if server in stats:
				stats[server][name] = value
	return stats


def instances(servers):
	"""Prometheus matcher for the whole fleet. Its regexes are anchored, so alternation is safe.

	The dots need two backslashes: PromQL unescapes the string literal before it reads the regex.
	"""
	return "|".join(server.replace(".", r"\\.") for server in servers)


def latest_values(query, end, key=lambda metric: metric.get("instance")):
	"""Last point of every series up to `end`, keyed by label. A gap and a NaN both read as zero.

	The window lives inside the query, so ask Prometheus for a short range only. A range as
	long as the window rounds to whole window boundaries and hides the last several minutes.
	"""
	end = end.replace(tzinfo=ZoneInfo(get_system_timezone()))  # Prometheus reads epoch seconds
	datasets = prometheus_query(
		query, key, "Asia/Kolkata", 120, 60, use_timestamps=True, start=end - timedelta(seconds=120), end=end
	)["datasets"]
	values = {}
	for dataset in datasets:
		points = [point for point in dataset["values"] if point is not None]
		values[dataset["name"]] = last_number(points)
	return values


def last_number(points):
	"""A series with no points, and one that ends in a NaN, both read as zero."""
	if not points or math.isnan(points[-1]):
		return 0
	return points[-1]


class DiskUsage:
	"""Used percent per mountpoint. A mountpoint on two or more servers gets its own column."""

	def __init__(self, servers, end):
		self.used = get_fleet_disk_usage(servers, end)
		counts = Counter(mountpoint for mounts in self.used.values() for mountpoint in mounts)
		common = [mountpoint for mountpoint, count in counts.items() if count > 1]
		self.common = sorted(common, key=lambda mountpoint: (mountpoint == "/boot/efi", mountpoint))

	def columns(self):
		columns = [
			{"fieldname": f"disk_{index}", "label": disk_label(mountpoint), "fieldtype": "Float"}
			for index, mountpoint in enumerate(self.common)
		]
		other = {
			"fieldname": "disk",
			"label": "Other Disk (% per mountpoint)",
			"fieldtype": "Data",
			"width": 320,
		}
		return [*columns, other]

	def cells(self, server):
		mounts = self.used[server]
		cells = {f"disk_{index}": mounts.get(mountpoint) for index, mountpoint in enumerate(self.common)}
		others = [
			f"{mountpoint} {percent}%"
			for mountpoint, percent in mounts.items()
			if mountpoint not in self.common
		]
		return {**cells, "disk": ", ".join(others)}


def disk_label(mountpoint):
	"""Bold the last directory, so .clones and .docker-builds stand out in a narrow header."""
	parent, _, name = mountpoint.rpartition("/")
	return f"Disk {parent}/<b>{name}</b> (%)"


def get_fleet_disk_usage(servers, end):
	"""Used percent of every real disk and volume, as {server: {mountpoint: percent}}."""
	filesystem = f'job="node", instance=~"{instances(servers)}", fstype!~"tmpfs|squashfs|overlay|fuse.lxcfs"'
	used = latest_values(
		f"100 * (1 - node_filesystem_avail_bytes{{{filesystem}}}"
		f" / node_filesystem_size_bytes{{{filesystem}}})",
		end,
		lambda metric: (metric.get("instance"), metric.get("device"), metric.get("mountpoint")),
	)
	return one_mountpoint_per_device(used, servers)


def one_mountpoint_per_device(used, servers):
	"""A bind mount shares its device with the volume. Keep the volume, else the shortest path."""
	mountpoints = {server: {} for server in servers}
	seen = set()
	for (server, device, mountpoint), percent in sorted(
		used.items(), key=lambda item: mount_rank(item[0][2])
	):
		if percent and server in mountpoints and (server, device) not in seen:
			seen.add((server, device))
			mountpoints[server][mountpoint] = rounded(percent, 1)
	return mountpoints


def mount_rank(mountpoint):
	"""/home/frappe/benches is as long as /opt/volumes/benches, and /var/lib/docker is shorter."""
	return (not mountpoint.startswith(VOLUMES), len(mountpoint), mountpoint)


def percentile(values, fraction):
	"""Nearest rank. Good enough for a handful of builds, and correct at both ends."""
	if not values:
		return 0
	values = sorted(values)
	return values[min(int(len(values) * fraction), len(values) - 1)]


def get_builds(period):
	"""Builds that started inside the period."""
	return frappe.get_all(
		"Deploy Candidate Build",
		{
			"build_start": ("between", (period.start, period.end)),
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


def get_pull_seconds(period):
	"""Median New Bench job. Every one pulls an image, so it tracks how fast the registry serves."""
	jobs = frappe.get_all(
		"Agent Job",
		{
			"job_type": "New Bench",
			"status": "Success",
			"end": ("between", (period.start, period.end)),
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


def get_selected_chart(chart, period, builds, servers):
	if chart == "Build Failures by Cluster":
		return get_build_failure_chart(period.seconds, builds, servers)
	if chart == "New Bench Failures by Cluster":
		return get_new_bench_failure_chart(period)
	if chart == "Remote Builder Failures by Build Server":
		events = [(job.failed_at, job.server) for job in get_failed_jobs("Run Remote Builder", period)]
		return stacked_chart("Failed Run Remote Builder jobs", period.seconds, events)
	if chart == "Build Failures by Build Server":
		return get_failed_builds_by_server_chart(period)
	if chart == "Build Duration by Build Server":
		return get_build_duration_chart(builds)
	if chart == "New Bench Jobs by Status":
		return get_new_bench_jobs_chart(period)
	if chart == "Prune Jobs by Server":
		return get_prune_chart(period)
	return get_chart(period.seconds, builds)


def get_prune_chart(period):
	plays = frappe.get_all(
		"Ansible Play",
		{
			"playbook": ("in", ("docker_system_prune.yml", "prune_mirror_registry.yml")),
			"creation": ("between", (period.start, period.end)),
		},
		["creation", "server"],
	)
	return stacked_chart("Prune plays", period.seconds, [(play.creation, play.server) for play in plays])


def get_failed_builds_by_server_chart(period):
	builds = frappe.get_all(
		"Deploy Candidate Build",
		{"creation": ("between", (period.start, period.end)), "status": "Failure"},
		["creation", "build_server"],
	)
	events = [(build.creation, build.build_server or "No build server") for build in builds]
	return stacked_chart("Failed builds by creation", period.seconds, events)


def get_new_bench_jobs_chart(period):
	jobs = frappe.get_all(
		"Agent Job",
		{"job_type": "New Bench", "creation": ("between", (period.start, period.end))},
		["creation", "status"],
	)
	chart = stacked_chart("New Bench jobs", period.seconds, [(job.creation, job.status) for job in jobs])
	colors = {"Success": "green", "Failure": "red", "Delivery Failure": "orange", "Running": "blue"}
	chart["colors"] = [colors.get(dataset["name"], "grey") for dataset in chart["data"]["datasets"]]
	return chart


def get_build_duration_chart(builds):
	"""Histogram of successful build minutes, about twelve bins, stacked by build server."""
	spans = [
		((build.build_end - build.build_start).total_seconds(), build.build_server)
		for build in builds
		if build.status == "Success" and build.build_end
	]
	longest = max((seconds for seconds, _ in spans), default=0)
	width = max(60, math.ceil(longest / 12 / 60) * 60)  # whole minutes
	counts = Counter((int(seconds // width), server) for seconds, server in spans)
	bins = range(max((index for index, _ in counts), default=-1) + 1)
	servers = sorted({server for _, server in counts})
	return {
		"title": "Successful builds by duration",
		"data": {
			"labels": [f"{index * width // 60}-{(index + 1) * width // 60} min" for index in bins],
			"datasets": [
				{"name": server, "values": [counts[(index, server)] for index in bins]} for server in servers
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}


def get_new_bench_failure_chart(period):
	jobs = get_failed_jobs("New Bench", period)
	servers = {job.server for job in jobs}
	cluster_of = dict(frappe.get_all("Server", {"name": ("in", servers)}, ["name", "cluster"], as_list=True))
	events = [(job.failed_at, cluster_of.get(job.server)) for job in jobs]
	return stacked_chart("Failed New Bench jobs", period.seconds, events)


def get_build_failure_chart(window, builds, servers):
	# ponytail: a build on a server that is no longer active reads as "No cluster"
	cluster_of = {server.name: server.cluster for server in servers}
	events = [
		(build.build_start, cluster_of.get(build.build_server))
		for build in builds
		if build.status == "Failure"
	]
	return stacked_chart("Failed builds", window, events)


def get_failed_jobs(job_type, period):
	"""Failed jobs, at the time they ended. A Delivery Failure has no end, so its creation counts."""
	job = frappe.qb.DocType("Agent Job")
	return (
		frappe.qb.from_(job)
		.select(job.server, Coalesce(job.end, job.creation).as_("failed_at"))
		.where(job.job_type == job_type)
		.where(job.status.isin(("Failure", "Delivery Failure")))
		.where(Coalesce(job.end, job.creation)[period.start : period.end])
		.run(as_dict=True)
	)


def stacked_chart(title, window, events):
	"""Events per bucket, one stacked series per group. An event is a (moment, group) pair."""
	bucket = max(60, window // 12)
	counts = Counter((floor_to_bucket(moment, bucket), group or "No cluster") for moment, group in events)
	labels = sorted({moment for moment, _ in counts})
	groups = sorted({group for _, group in counts})
	return {
		"title": f"{title} per {bucket // 60} minutes",
		"data": {
			"labels": [label.strftime("%d %b %H:%M") for label in labels],
			"datasets": [
				{"name": group, "values": [counts[(label, group)] for label in labels]} for group in groups
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}


def floor_to_bucket(moment, bucket):
	return datetime.fromtimestamp(moment.timestamp() // bucket * bucket)


def get_cluster_loss(period):
	"""Packet loss per cluster, above the table. A bad region shows here before a server does."""
	window = period.seconds
	retransmit = latest_values(
		f'avg by (cluster) (rate(node_netstat_Tcp_RetransSegs{{job="node"}}[{window}s])'
		f' / rate(node_netstat_Tcp_OutSegs{{job="node"}}[{window}s])) * 100',
		period.end,
		lambda metric: metric.get("cluster") or "No cluster",
	)
	drops = latest_values(
		f'sum by (cluster) (rate(node_network_receive_drop_total{{job="node", device!="lo"}}[{window}s])'
		f' + rate(node_network_transmit_drop_total{{job="node", device!="lo"}}[{window}s]))',
		period.end,
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
