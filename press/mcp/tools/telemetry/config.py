# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import Any

MAX_LIMIT = 1000
MAX_LOG_CHARS = 20000
MAX_LOG_LINES = 5000
DEFAULT_TIMEOUT = 120
EXPORTER_SCRAPE_INTERVAL = "5m"
MAX_RANGE_SECONDS = 30 * 24 * 60 * 60
MIN_STEP_SECONDS = 60
MAX_RELATIVE_MINUTES = 30 * 24 * 60

SERVER_TYPE_MAP = {
	"Proxy Server": "proxy",
	"Server": "app",
	"NFS Server": "nfs",
	"Database Server": "database",
	"NAT Server": "nat",
}

SERVER_METRICS: dict[str, dict[str, str]] = {
	"cpu": {
		"name": "CPU",
		"function": "press.api.server.analytics(query='cpu')",
		"source": "prometheus",
		"job": "node",
		"query": 'sum by (mode)(rate(node_cpu_seconds_total{instance="$server", job="node"}[$step])) * 100',
		"group_by": "mode",
	},
	"loadavg": {
		"name": "Load average",
		"function": "press.api.server.analytics(query='loadavg')",
		"source": "prometheus",
		"job": "node",
		"query": '{__name__=~"node_load1|node_load5|node_load15", instance="$server", job="node"}',
		"group_by": "__name__",
	},
	"memory": {
		"name": "Memory",
		"function": "press.api.server.analytics(query='memory')",
		"source": "prometheus",
		"job": "node",
		"query": (
			'node_memory_MemTotal_bytes{instance="$server",job="node"}'
			' - node_memory_MemFree_bytes{instance="$server",job="node"}'
			' - (node_memory_Cached_bytes{instance="$server",job="node"}'
			' + node_memory_Buffers_bytes{instance="$server",job="node"})'
		),
		"group_by": "Used",
	},
	"network": {
		"name": "Network",
		"function": "press.api.server.analytics(query='network')",
		"source": "prometheus",
		"job": "node",
		"query": 'rate(node_network_receive_bytes_total{instance="$server", job="node", device=~"ens.*"}[$step]) * 8',
		"group_by": "device",
	},
	"iops": {
		"name": "Disk I/O",
		"function": "press.api.server.analytics(query='iops')",
		"source": "prometheus",
		"job": "node",
		"query": 'rate(node_disk_reads_completed_total{instance="$server", job="node"}[$step])',
		"group_by": "device",
	},
	"space": {
		"name": "Disk space",
		"function": "press.api.server.analytics(query='space')",
		"source": "prometheus",
		"job": "node",
		"query": (
			'100 - ((node_filesystem_avail_bytes{instance="$server", job="node", mountpoint=~"$mountpoint"}'
			' * 100) / node_filesystem_size_bytes{instance="$server", job="node", mountpoint=~"$mountpoint"})'
		),
		"group_by": "mountpoint",
	},
	"database_uptime": {
		"name": "Database uptime",
		"function": "press.api.server.analytics(query='database_uptime')",
		"source": "prometheus",
		"job": "mariadb",
		"query": 'mysql_up{instance="$server",job="mariadb"}',
		"group_by": "Uptime",
	},
	"database_commands_count": {
		"name": "Database commands count",
		"function": "press.api.server.analytics(query='database_commands_count')",
		"source": "prometheus",
		"job": "mariadb",
		"query": (
			'sum(round(increase(mysql_global_status_commands_total{instance="$server", '
			'command=~"select|update|insert|delete|begin|commit|rollback"}[$step]))) by (command)'
		),
		"group_by": "command",
	},
	"database_connections": {
		"name": "Database connections",
		"function": "press.api.server.analytics(query='database_connections')",
		"source": "prometheus",
		"job": "mariadb",
		"query": (
			'{__name__=~"mysql_global_status_threads_connected|mysql_global_variables_max_connections", '
			'instance="$server"}'
		),
		"group_by": "__name__",
	},
	"innodb_bp_size": {
		"name": "InnoDB buffer pool size",
		"function": "press.api.server.analytics(query='innodb_bp_size')",
		"source": "prometheus",
		"job": "mariadb",
		"query": 'mysql_global_variables_innodb_buffer_pool_size{instance="$server"}',
		"group_by": "Buffer Pool Size",
	},
	"innodb_bp_size_of_total_ram": {
		"name": "InnoDB buffer pool size of total RAM",
		"function": "press.api.server.analytics(query='innodb_bp_size_of_total_ram')",
		"source": "prometheus",
		"job": "mariadb+node",
		"query": (
			'avg by (instance) ((mysql_global_variables_innodb_buffer_pool_size{instance=~"$server"} * 100))'
			' / on (instance) (avg by (instance) (node_memory_MemTotal_bytes{instance=~"$server"}))'
		),
		"group_by": "instance",
	},
	"innodb_bp_miss_percent": {
		"name": "InnoDB buffer pool miss percent",
		"function": "press.api.server.analytics(query='innodb_bp_miss_percent')",
		"source": "prometheus",
		"job": "mariadb",
		"query": (
			'avg by (instance) (rate(mysql_global_status_innodb_buffer_pool_reads{instance=~"$server"}[$step])'
			' / rate(mysql_global_status_innodb_buffer_pool_read_requests{instance=~"$server"}[$step]))'
		),
		"group_by": "instance",
	},
	"innodb_avg_row_lock_time": {
		"name": "InnoDB average row lock time",
		"function": "press.api.server.analytics(query='innodb_avg_row_lock_time')",
		"source": "prometheus",
		"job": "mariadb",
		"query": (
			'(rate(mysql_global_status_innodb_row_lock_time{instance="$server"}[$step]) / 1000)'
			' / rate(mysql_global_status_innodb_row_lock_waits{instance="$server"}[$step])'
		),
		"group_by": "Avg Row Lock Time",
	},
}

RELEASE_GROUP_METRICS: dict[str, dict[str, str]] = {
	"cpu": {
		"name": "CPU",
		"function": "press.api.analytics.get_cpu_usage",
		"query": 'sum by (name) (rate(container_cpu_usage_seconds_total{job="cadvisor", name=~"$benches"}[5m]))',
	},
	"memory": {
		"name": "Memory",
		"function": "press.api.analytics.get_memory_usage",
		"query": (
			'sum by (name) (avg_over_time(container_memory_usage_bytes{job="cadvisor", '
			'name=~"$benches"}[5m]) / 1024 / 1024 / 1024)'
		),
	},
	"fs_reads": {
		"name": "Filesystem reads",
		"function": "press.api.analytics.get_fs_read_bytes",
		"query": 'sum by (name) (rate(container_fs_reads_bytes_total{job="cadvisor", name=~"$benches"}[5m]))',
	},
	"fs_writes": {
		"name": "Filesystem writes",
		"function": "press.api.analytics.get_fs_write_bytes",
		"query": 'sum by (name) (rate(container_fs_writes_bytes_total{job="cadvisor", name=~"$benches"}[5m]))',
	},
	"network_in": {
		"name": "Network in",
		"function": "press.api.analytics.get_incoming_network_traffic",
		"query": (
			'sum by (name) (rate(container_network_receive_bytes_total{job="cadvisor", '
			'name=~"$benches"}[5m]))'
		),
	},
	"network_out": {
		"name": "Network out",
		"function": "press.api.analytics.get_outgoing_network_traffic",
		"query": (
			'sum by (name) (rate(container_network_transmit_bytes_total{job="cadvisor", '
			'name=~"$benches"}[5m]))'
		),
	},
}

LOG_FIELDS = [
	"@timestamp",
	"agent.name",
	"json.site",
	"json.transaction_type",
	"json.duration",
	"json.request.path",
	"json.request.counter",
	"json.job.method",
	"json.uuid",
	"source.ip",
	"http.request.site",
	"http.request.duration",
	"mysql.slowlog.current_user",
	"mysql.slowlog.query",
	"event.duration",
]

GUIDES: dict[str, dict[str, Any]] = {
	"site": {
		"name": "Site",
		"title": "Site telemetry",
		"use_for": "Site uptime, request volume, CPU time, slow paths, background jobs and request logs.",
		"prometheus": {
			"exporters": ["blackbox/site uptime"],
			"examples": [
				'avg_over_time(probe_success{job="site", instance="<site-name>"}[5m])',
				'min_over_time(probe_success{job="site", instance="<site-name>"}[1h])',
			],
		},
		"elasticsearch": {
			"index": "filebeat-*",
			"fields": LOG_FIELDS,
			"examples": [
				{
					"size": 10,
					"sort": {"@timestamp": "desc"},
					"query": {
						"bool": {
							"filter": [
								{"match_phrase": {"json.transaction_type": "request"}},
								{"match_phrase": {"json.site": "<site-name>"}},
								{"range": {"@timestamp": {"gte": "now-1h"}}},
							],
							"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
						}
					},
				}
			],
		},
	},
	"bench": {
		"name": "Bench",
		"title": "Bench and release group telemetry",
		"use_for": "Container CPU, memory, filesystem, network, bench logs and supervisor processes.",
		"prometheus": {"exporters": ["cadvisor", "gunicorn"], "metrics": RELEASE_GROUP_METRICS},
		"logs": {"tools": ["get_bench_log", "get_bench_processes"]},
	},
	"server": {
		"name": "Server",
		"title": "Server telemetry",
		"use_for": "App, database, proxy, registry, log and monitor server health.",
		"prometheus": {"scrape_interval": EXPORTER_SCRAPE_INTERVAL, "metrics": SERVER_METRICS},
		"elasticsearch": {"index": "filebeat-*", "fields": LOG_FIELDS},
	},
	"logs": {
		"name": "Logs",
		"title": "Log lookup",
		"use_for": "Request logs, background job logs, nginx access data, slow logs and deadlock reports.",
		"elasticsearch": {"index": "filebeat-*", "fields": LOG_FIELDS},
		"file_logs": {"tool": "get_site_or_bench_log"},
	},
	"trace_id": {
		"name": "Trace ID",
		"title": "Trace ID lookup",
		"use_for": "Map FRAPPE_TRACE_ID to request/job log and matching slow SQL logs.",
		"elasticsearch": {
			"index": "filebeat-*",
			"fields": ["json.uuid", "json.site", "json.transaction_type", "mysql.slowlog.query"],
		},
	},
}
