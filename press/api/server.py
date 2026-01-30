# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as tz
from typing import TYPE_CHECKING, TypedDict

import frappe
import requests
from frappe.utils import convert_utc_to_timezone, flt
from frappe.utils.caching import redis_cache
from frappe.utils.password import get_decrypted_password

from press.api.analytics import TIMESPAN_TIMEGRAIN_MAP, get_rounded_boundaries
from press.api.bench import all as all_benches
from press.api.site import protected
from press.exceptions import MonitorServerDown
from press.press.doctype.auto_scale_record.auto_scale_record import validate_scaling_schedule
from press.press.doctype.cloud_provider.cloud_provider import get_cloud_providers
from press.press.doctype.server_plan_type.server_plan_type import get_server_plan_types
from press.press.doctype.site_plan.plan import Plan, filter_by_roles
from press.press.doctype.team.team import get_child_team_members
from press.utils import get_current_team

if TYPE_CHECKING:
	from press.press.doctype.auto_scale_record.auto_scale_record import AutoScaleRecord
	from press.press.doctype.cluster.cluster import Cluster
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server
	from press.press.doctype.server_plan.server_plan import ServerPlan


class UnifiedServerDetails(TypedDict):
	title: str
	cluster: str
	app_plan: str
	auto_increase_storage: bool | None


def poly_get_doc(doctypes, name):
	for doctype in doctypes:
		if frappe.db.exists(doctype, name):
			return frappe.get_doc(doctype, name)
	return frappe.get_doc(doctypes[-1], name)


def get_mount_point(server: str, server_type=None) -> str:
	"""Guess mount point from server"""
	if server_type is None:
		server_type = "Database Server" if server[0] == "m" else "Server"

	elif server_type == "Application Server":
		server_type = "Server"

	elif server_type == "Replication Server":
		server_type = "Database Server"

	server_doc: "Server" | "DatabaseServer" = frappe.get_doc(server_type, server)
	if server_doc.provider != "AWS EC2":
		return "/"

	return server_doc.guess_data_disk_mountpoint()


@frappe.whitelist()
def all(server_filter=None):  # noqa: C901
	if server_filter is None:
		server_filter = {"server_type": "", "tag": ""}

	team = get_current_team()
	child_teams = [team.name for team in get_child_team_members(team)]
	teams = [team, *child_teams]

	db_server = frappe.qb.DocType("Database Server")
	app_server = frappe.qb.DocType("Server")
	res_tag = frappe.qb.DocType("Resource Tag")

	if server_filter["server_type"] != "Database Servers":
		app_server_query = (
			frappe.qb.from_(app_server)
			.select(
				app_server.name,
				app_server.title,
				app_server.status,
				app_server.creation,
				app_server.cluster,
			)
			.where(((app_server.team).isin(teams)) & (app_server.status != "Archived"))
		)

		if server_filter["tag"]:
			app_server_query = app_server_query.inner_join(res_tag).on(
				(res_tag.parent == app_server.name) & (res_tag.tag_name == server_filter["tag"])
			)

	if server_filter["server_type"] != "App Servers":
		database_server_query = (
			frappe.qb.from_(db_server)
			.select(
				db_server.name,
				db_server.title,
				db_server.status,
				db_server.creation,
				db_server.cluster,
			)
			.where(((db_server.team).isin(teams)) & (db_server.status != "Archived"))
		)

		if server_filter["tag"]:
			database_server_query = database_server_query.inner_join(res_tag).on(
				(res_tag.parent == db_server.name) & (res_tag.tag_name == server_filter["tag"])
			)

	if server_filter["server_type"] == "App Servers":
		query = app_server_query
	elif server_filter["server_type"] == "Database Servers":
		query = database_server_query
	else:
		query = app_server_query + database_server_query

	# union isn't supported in qb for run method
	# https://github.com/frappe/frappe/issues/15609
	servers = frappe.db.sql(query.get_sql(), as_dict=True)
	for server in servers:
		server_plan_name = frappe.get_value("Server", server.name, "plan")
		server["plan"] = frappe.get_doc("Server Plan", server_plan_name) if server_plan_name else None
		server["app_server"] = f"f{server.name[1:]}"
		server["tags"] = frappe.get_all("Resource Tag", {"parent": server.name}, pluck="tag_name")
		server["region_info"] = frappe.db.get_value(
			"Cluster", server.cluster, ["title", "image"], as_dict=True
		)
	return servers


@frappe.whitelist()
def server_tags():
	team = get_current_team()
	return frappe.get_all("Press Tag", {"team": team, "doctype_name": "Server"}, pluck="tag")


@frappe.whitelist()
@protected(["Server", "Database Server"])
def get(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	return {
		"name": server.name,
		"title": server.title,
		"status": server.status,
		"team": server.team,
		"app_server": server.name
		if server.is_self_hosted
		else f"f{server.name[1:]}",  # Don't use `f` series if self hosted
		"region_info": frappe.db.get_value(
			"Cluster", server.cluster, ["name", "title", "image"], as_dict=True
		),
		"server_tags": [{"name": x.tag, "tag": x.tag_name} for x in server.tags],
		"tags": frappe.get_all("Press Tag", {"team": server.team, "doctype_name": "Server"}, ["name", "tag"]),
		"type": "database-server" if server.meta.name == "Database Server" else "server",
	}


@frappe.whitelist()
@protected(["Server", "Database Server"])
def overview(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	plan = frappe.get_doc("Server Plan", server.plan) if server.plan else None
	if plan:
		# override plan disk size with the actual disk size
		# TODO: Remove this once we remove old dashboard
		plan.disk = frappe.db.get_value("Virtual Machine", name, "disk_size")

	return {
		"plan": plan if plan else None,
		"info": {
			"owner": frappe.db.get_value(
				"User",
				frappe.get_value("Team", server.team, "user"),
				["first_name", "last_name", "user_image"],
				as_dict=True,
			),
			"created_on": server.creation,
		},
	}


@frappe.whitelist()
@protected(["Server", "Database Server"])
def archive(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	server.drop_server()


@frappe.whitelist()
@protected(["Server"])
def get_reclaimable_size(name):
	server: Server = frappe.get_doc("Server", name)
	return server.agent.get("server/reclaimable-size")


@frappe.whitelist()
def new_unified(server: UnifiedServerDetails):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")

	cluster: Cluster = frappe.get_doc("Cluster", server["cluster"])

	app_plan: ServerPlan = frappe.get_doc("Server Plan", server["app_plan"])
	if not cluster.check_machine_availability(app_plan.instance_type):
		frappe.throw(
			f"No machines of {app_plan.instance_type} are currently available in the {cluster.name} region"
		)

	auto_increase_storage = server.get("auto_increase_storage", False)

	proxy_server = frappe.get_all(
		"Proxy Server",
		{"status": "Active", "cluster": cluster.name, "is_primary": True},
		limit=1,
	)[0]

	cluster.proxy_server = proxy_server.get("name")
	server_doc, database_server_doc, job = cluster.create_unified_server(
		server["title"], app_plan, team=team.name, auto_increase_storage=auto_increase_storage
	)
	return {"server": server_doc.name, "database_server": database_server_doc.name, "job": job.name}


@frappe.whitelist()
def new(server):
	server_plan_platform = frappe.get_value("Server Plan", server["app_plan"], "platform")
	cluster_has_arm_support = frappe.get_value("Cluster", server["cluster"], "has_arm_support")
	auto_increase_storage = server.get("auto_increase_storage", False)

	if server_plan_platform == "arm64" and not cluster_has_arm_support:
		frappe.throw(f"ARM Instances are currently unavailable in the {server['cluster']} region")

	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")

	cluster: Cluster = frappe.get_doc("Cluster", server["cluster"])

	db_plan: ServerPlan = frappe.get_doc("Server Plan", server["db_plan"])
	if not cluster.check_machine_availability(db_plan.instance_type):
		frappe.throw(
			f"No machines of {db_plan.instance_type} are currently available in the {cluster.name} region"
		)

	db_server, job = cluster.create_server(
		"Database Server",
		server["title"],
		db_plan,
		team=team.name,
		auto_increase_storage=auto_increase_storage,
	)

	proxy_server = frappe.get_all(
		"Proxy Server",
		{"status": "Active", "cluster": cluster.name, "is_primary": True},
		limit=1,
	)[0]

	# to be used by app server
	cluster.database_server = db_server.name
	cluster.proxy_server = proxy_server.name

	app_plan: ServerPlan = frappe.get_doc("Server Plan", server["app_plan"])
	if not cluster.check_machine_availability(app_plan.instance_type):
		frappe.throw(
			f"No machines of {app_plan.instance_type} are currently available in the {cluster.name} region"
		)

	app_server, job = cluster.create_server(
		"Server", server["title"], app_plan, team=team.name, auto_increase_storage=auto_increase_storage
	)

	return {"server": app_server.name, "job": job.name}


def get_cpu_and_memory_usage(name: str, time_range: str = "4m") -> dict[str, float]:
	"""Returns simplified CPU and memory usage [0..1] for autoscale triggers"""
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return {"vcpu": 0.0, "memory": 0.0}

	query = f"""
		1 - avg(rate(node_cpu_seconds_total{{instance="{name}",job="node",mode="idle"}}[{time_range}]))

			OR

		1 -
			(
				avg_over_time(node_memory_MemAvailable_bytes{{instance="{name}", job="node"}}[{time_range}])
				/
				avg_over_time(node_memory_MemTotal_bytes{{instance="{name}", job="node"}}[{time_range}])
			)
	"""

	url = f"https://{monitor_server}/prometheus/api/v1/query"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")
	params = {"query": query}

	response = requests.get(url, params=params, auth=("frappe", str(password))).json()

	if (
		response.get("status") == "success"
		and response.get("data")
		and response["data"].get("resultType") == "vector"
		and response["data"].get("result")
	):
		results = response["data"]["result"]
		if results and len(results) == 2:
			return {
				"vcpu": float(results[0]["value"][1]),
				"memory": float(results[1]["value"][1]),
			}

	return {"vcpu": 0.0, "memory": 0.0}


@frappe.whitelist()
@protected(["Server", "Database Server"])
def usage(name):
	mount_point = get_mount_point(name)
	# 	  (
	#       (count(count by (cpu) (node_cpu_seconds_total{instance="fs22-mumbai.frappe.cloud",job="node"})))
	#     -
	#       avg(
	#         sum by (mode) (
	#           rate(node_cpu_seconds_total{instance="fs22-mumbai.frappe.cloud",job="node",mode="idle"}[120s])
	#         )
	#       )
	#   )
	# /
	# Changing CPU usage to a vector result averaging over a 120s window

	query_map = {
		"disk": (
			f"""sum(node_filesystem_size_bytes{{instance="{name}", job="node", mountpoint=~"{mount_point}"}} - node_filesystem_avail_bytes{{instance="{name}", job="node", mountpoint=~"{mount_point}"}}) by ()/ (1024 * 1024 * 1024)""",
			lambda x: x,
		),
		"memory": (
			f"""(node_memory_MemTotal_bytes{{instance="{name}",job="node"}} - node_memory_MemFree_bytes{{instance="{name}",job="node"}} - (node_memory_Cached_bytes{{instance="{name}",job="node"}} + node_memory_Buffers_bytes{{instance="{name}",job="node"}})) / (1024 * 1024)""",
			lambda x: x,
		),
		"free_memory": (
			f"""avg_over_time(node_memory_MemAvailable_bytes{{instance="{name}", job="node"}}[10m])""",
			lambda x: x,
		),
	}

	result = {}
	for usage_type, query in query_map.items():
		response = prometheus_query(query[0], query[1], "Asia/Kolkata", 120, 120)["datasets"]
		if response:
			result[usage_type] = response[0]["values"][-1]

	result["vcpu"] = get_cpu_and_memory_usage(name)["vcpu"]
	return result


@protected(["Server", "Database Server"])
def total_resource(name):
	mount_point = get_mount_point(name)
	query_map = {
		"vcpu": (
			f"""(count(count(node_cpu_seconds_total{{instance="{name}",job="node"}}) by (cpu)))""",
			lambda x: x,
		),
		"disk": (
			f"""sum(node_filesystem_size_bytes{{instance="{name}", job="node", mountpoint=~"{mount_point}"}}) by () / (1024 * 1024 * 1024)""",
			lambda x: x,
		),
		"memory": (
			f"""(node_memory_MemTotal_bytes{{instance="{name}",job="node"}}) / (1024 * 1024)""",
			lambda x: x,
		),
	}

	result = {}
	for usage_type, query in query_map.items():
		response = prometheus_query(query[0], query[1], "Asia/Kolkata", 120, 120)["datasets"]
		if response:
			result[usage_type] = response[0]["values"][-1]
	return result


def calculate_swap(name):
	query_map = {
		"swap_used": (
			f"""((node_memory_SwapTotal_bytes{{instance="{name}",job="node"}} - node_memory_SwapFree_bytes{{instance="{name}",job="node"}}) / node_memory_SwapTotal_bytes{{instance="{name}",job="node"}}) * 100""",
			lambda x: x,
		),
		"swap": (
			f"""node_memory_SwapTotal_bytes{{instance="{name}",job="node"}} / (1024 * 1024 * 1024)""",
			lambda x: x,
		),
		"required": (
			f"""(
					(node_memory_MemTotal_bytes{{instance="{name}",job="node"}} +
						node_memory_SwapTotal_bytes{{instance="{name}",job="node"}}
					) -
					(node_memory_MemFree_bytes{{instance="{name}",job="node"}} +
						node_memory_SwapFree_bytes{{instance="{name}",job="node"}} +
						node_memory_Cached_bytes{{instance="{name}",job="node"}} +
						node_memory_Buffers_bytes{{instance="{name}",job="node"}} +
						node_memory_SwapCached_bytes{{instance="{name}",job="node"}}
					)
				) /
				(1024 * 1024 * 1024)""",
			lambda x: x,
		),
	}

	result = {}
	for usage_type, query in query_map.items():
		response = prometheus_query(query[0], query[1], "Asia/Kolkata", 120, 120)["datasets"]
		if response:
			result[usage_type] = response[0]["values"][-1]
	return result


@frappe.whitelist()
@protected(["Server", "Database Server"])
@redis_cache(ttl=10 * 60)
def analytics(name, query, timezone, duration, server_type=None):
	# If the server type is of unified server, then just show server's metrics as application server
	server_type = "Application Server" if server_type == "Unified Server" else server_type
	mount_point = get_mount_point(name, server_type)
	timespan, timegrain = get_timespan_timegrain(duration)

	query_map = {
		"cpu": (
			f"""sum by (mode)(rate(node_cpu_seconds_total{{instance="{name}", job="node"}}[{timegrain}s])) * 100""",
			lambda x: x["mode"],
		),
		"network": (
			f"""rate(node_network_receive_bytes_total{{instance="{name}", job="node", device=~"ens.*"}}[{timegrain}s]) * 8""",
			lambda x: x["device"],
		),
		"iops": (
			f"""rate(node_disk_reads_completed_total{{instance="{name}", job="node"}}[{timegrain}s])""",
			lambda x: x["device"],
		),
		"space": (
			f"""100 - ((node_filesystem_avail_bytes{{instance="{name}", job="node", mountpoint=~"{mount_point}"}} * 100) / node_filesystem_size_bytes{{instance="{name}", job="node", mountpoint=~"{mount_point}"}})""",
			lambda x: x["mountpoint"],
		),
		"loadavg": (
			f"""{{__name__=~"node_load1|node_load5|node_load15", instance="{name}", job="node"}}""",
			lambda x: f"Load Average {x['__name__'][9:]}",  # strip "node_load" prefix
		),
		"memory": (
			f"""node_memory_MemTotal_bytes{{instance="{name}",job="node"}} - node_memory_MemFree_bytes{{instance="{name}",job="node"}} - (node_memory_Cached_bytes{{instance="{name}",job="node"}} + node_memory_Buffers_bytes{{instance="{name}",job="node"}})""",
			lambda x: "Used",
		),
		"database_uptime": (
			f"""mysql_up{{instance="{name}",job="mariadb"}}""",
			lambda x: "Uptime",
		),
		"database_commands_count": (
			f"""sum(round(increase(mysql_global_status_commands_total{{instance='{name}', command=~"select|update|insert|delete|begin|commit|rollback"}}[{timegrain}s]))) by (command)""",
			lambda x: x["command"],
		),
		"database_connections": (
			f"""{{__name__=~"mysql_global_status_threads_connected|mysql_global_variables_max_connections", instance="{name}"}}""",
			lambda x: "Max Connections"
			if x["__name__"] == "mysql_global_variables_max_connections"
			else "Connected Clients",
		),
		"innodb_bp_size": (
			f"""mysql_global_variables_innodb_buffer_pool_size{{instance='{name}'}}""",
			lambda x: "Buffer Pool Size",
		),
		"innodb_bp_size_of_total_ram": (
			f"""avg by (instance) ((mysql_global_variables_innodb_buffer_pool_size{{instance=~"{name}"}} * 100)) / on (instance) (avg by (instance) (node_memory_MemTotal_bytes{{instance=~"{name}"}}))""",
			lambda x: "Buffer Pool Size of Total Ram",
		),
		"innodb_bp_miss_percent": (
			f"""
avg by (instance) (
		rate(mysql_global_status_innodb_buffer_pool_reads{{instance=~"{name}"}}[{timegrain}s])
		/
		rate(mysql_global_status_innodb_buffer_pool_read_requests{{instance=~"{name}"}}[{timegrain}s])
)
""",
			lambda x: "Buffer Pool Miss Percentage",
		),
		"innodb_avg_row_lock_time": (
			f"""(rate(mysql_global_status_innodb_row_lock_time{{instance="{name}"}}[{timegrain}s]) / 1000)/rate(mysql_global_status_innodb_row_lock_waits{{instance="{name}"}}[{timegrain}s])""",
			lambda x: "Avg Row Lock Time",
		),
	}

	return prometheus_query(query_map[query][0], query_map[query][1], timezone, timespan, timegrain)


@frappe.whitelist()
@protected(["Server", "Database Server"])
@redis_cache(ttl=10 * 60)
def get_request_by_site(name, query, timezone, duration):
	from frappe.utils import add_to_date, now_datetime
	from pytz import timezone as pytz_timezone

	from press.api.analytics import ResourceType, get_request_by_

	timespan, timegrain = get_timespan_timegrain(duration)

	end = now_datetime().astimezone(pytz_timezone(timezone))
	start = add_to_date(end, seconds=-timespan)

	timespan, timegrain = get_timespan_timegrain(duration)

	return get_request_by_(name, query, timezone, start, end, timespan, timegrain, ResourceType.SERVER)


@frappe.whitelist()
@protected(["Server", "Database Server"])
@redis_cache(ttl=10 * 60)
def get_background_job_by_site(name, query, timezone, duration):
	from frappe.utils import add_to_date, now_datetime
	from pytz import timezone as pytz_timezone

	from press.api.analytics import ResourceType, get_background_job_by_

	timespan, timegrain = get_timespan_timegrain(duration)

	end = now_datetime().astimezone(pytz_timezone(timezone))
	start = add_to_date(end, seconds=-timespan)

	return get_background_job_by_(name, query, timezone, start, end, timespan, timegrain, ResourceType.SERVER)


@frappe.whitelist()
@protected(["Server", "Database Server"])
@redis_cache(ttl=10 * 60)
def get_slow_logs_by_site(name, query, timezone, duration, normalize=False):
	from frappe.utils import add_to_date, now_datetime
	from pytz import timezone as pytz_timezone

	from press.api.analytics import ResourceType, get_slow_logs

	timespan, timegrain = get_timespan_timegrain(duration)

	end = now_datetime().astimezone(pytz_timezone(timezone))
	start = add_to_date(end, seconds=-timespan)

	return get_slow_logs(
		name, query, timezone, start, end, timespan, timegrain, ResourceType.SERVER, normalize
	)


def prometheus_query(query, function, timezone, timespan, timegrain):
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return {"datasets": [], "labels": []}

	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")

	start, end = get_rounded_boundaries(
		timespan,
		timegrain,
	)  # timezone not passed as only utc time allowed in promql

	query = {
		"query": query,
		"start": start.timestamp(),
		"end": end.timestamp(),
		"step": f"{timegrain}s",
	}

	try:
		response = requests.get(url, params=query, auth=("frappe", str(password))).json()
	except requests.exceptions.RequestException:
		frappe.throw("Unable to connect to monitor server", MonitorServerDown)

	datasets = []
	labels = []

	if not response["data"]["result"]:
		return {"datasets": datasets, "labels": labels}

	timegrain_delta = timedelta(seconds=timegrain)
	labels = [(start + i * timegrain_delta).timestamp() for i in range((end - start) // timegrain_delta + 1)]

	for index in range(len(response["data"]["result"])):
		dataset = {
			"name": function(response["data"]["result"][index]["metric"]),
			"values": [None] * len(labels),  # Initialize with None
		}
		for label, value in response["data"]["result"][index]["values"]:
			dataset["values"][labels.index(label)] = flt(value, 2)
		datasets.append(dataset)

	labels = [
		convert_utc_to_timezone(datetime.fromtimestamp(label, tz=tz.utc).replace(tzinfo=None), timezone)
		for label in labels
	]

	return {"datasets": datasets, "labels": labels}

@frappe.whitelist()
def options():
	if not get_current_team(get_doc=True).servers_enabled:
		frappe.throw("Servers feature is not yet enabled on your account")

	regions_filter = {"cloud_provider": ("!=", "Generic"), "public": True, "status": "Active"}
	is_system_user = (
		(frappe.session and frappe.session.data and frappe.session.data.user_type)
		or (
			frappe.session
			and frappe.session.user
			and frappe.get_cached_value("User", frappe.session.user, "user_type")
		)
	) == "System User"

	if is_system_user:
		regions_filter.pop("public", None)

	regions = frappe.get_all(
		"Cluster",
		regions_filter,
		[
			"name",
			"title",
			"image",
			"beta",
			"has_add_on_storage_support",
			"cloud_provider",
			"public",
			"has_unified_server_support",
			"default_app_server_plan",
			"default_app_server_plan_type",
			"default_db_server_plan",
			"default_db_server_plan_type",
			"by_default_select_unified_mode",
		],
	)

	if not is_system_user and not (
		frappe.local and frappe.local.team() and frappe.local.team().hetzner_internal_user
	):
		# filter out hetzner clusters
		regions = [region for region in regions if region.get("cloud_provider") != "Hetzner"]

	cloud_providers = get_cloud_providers()
	"""
	{
		"Mumbai": {
			"providers": ["AWS EC2", "OCI"],
			"image": "<chose any cluster image with same title>",
			"providers_data": {
				"AWS EC2": {
					"cluster_name": "aws-mumbai",
					"title": "Amazon Web Services",
					"provider_image": "...",
					"has_add_on_storage_support": 1,
					"has_unified_server_support": 1,
				},
			}
		}
	}
	"""
	regions_data = {}
	for region in regions:
		provider = region.get("cloud_provider")
		record = regions_data.setdefault(region.title, {"providers": {}})
		if region.image and not record.get("image"):
			record["image"] = region.image

		record["providers"][provider] = {
			"cluster_name": region.name,
			"title": cloud_providers[provider]["title"],
			"provider_image": cloud_providers[provider]["image"],
			"beta": region.get("beta", 0),
			"has_add_on_storage_support": region.get("has_add_on_storage_support", 0),
			"has_unified_server_support": region.get("has_unified_server_support", 0),
			"default_app_server_plan": region.get("default_app_server_plan"),
			"default_app_server_plan_type": region.get("default_app_server_plan_type"),
			"default_db_server_plan": region.get("default_db_server_plan"),
			"default_db_server_plan_type": region.get("default_db_server_plan_type"),
			"by_default_select_unified_mode": region.get("by_default_select_unified_mode"),
		}

	default_server_plan_type = frappe.db.get_single_value("Press Settings", "default_server_plan_type")
	server_plan_types = get_server_plan_types()

	storage_plan = frappe.db.get_value(
		"Server Storage Plan",
		{"enabled": 1},
		["price_inr", "price_usd"],
		as_dict=True,
	)
	snapshot_plan = frappe.db.get_value(
		"Server Snapshot Plan",
		{"enabled": 1},
		["price_inr", "price_usd"],
		as_dict=True,
	)
	return {
		"regions": regions,
		"regions_data": regions_data,
		"app_plans": plans("Server").get("plans", []),
		"db_plans": plans("Database Server").get("plans", []),
		"plan_types": server_plan_types,
		"default_plan_type": default_server_plan_type,
		"storage_plan": storage_plan,
		"snapshot_plan": snapshot_plan,
	}

@frappe.whitelist()
def get_autoscale_discount():
	return frappe.db.get_single_value("Press Settings", "autoscale_discount", cache=True)


@frappe.whitelist()
def secondary_server_plans(
	name,
	cluster=None,
	platform=None,
	current_plan: str | None = None,
):
	current_price = frappe.db.get_value("Server Plan", current_plan, "price_inr")
	ServerPlan = frappe.qb.DocType("Server Plan")
	HasRole = frappe.qb.DocType("Has Role")
	autoscale_discount = frappe.db.get_single_value("Press Settings", "autoscale_discount")

	query = (
		frappe.qb.from_(ServerPlan)
		.select(
			ServerPlan.name,
			ServerPlan.title,
			(ServerPlan.price_usd * autoscale_discount).as_("price_usd"),
			(ServerPlan.price_inr * autoscale_discount).as_("price_inr"),
			ServerPlan.vcpu,
			ServerPlan.memory,
			ServerPlan.disk,
			ServerPlan.cluster,
			ServerPlan.instance_type,
			ServerPlan.premium,
			ServerPlan.platform,
			HasRole.role,
		)
		.join(HasRole)
		.on((HasRole.parenttype == "Server Plan") & (HasRole.parent == ServerPlan.name))
		.where(ServerPlan.server_type == name)
		.where(ServerPlan.platform == platform)
		.where(ServerPlan.price_inr == current_price)
		.where(ServerPlan.enabled == 1)
	)
	if cluster:
		query = query.where(ServerPlan.cluster == cluster)
	if platform:
		query = query.where(ServerPlan.platform == platform)

	plans = query.run(as_dict=1)
	return filter_by_roles(plans)


@frappe.whitelist()
def plans(name, cluster=None, platform=None, resource_name=None, cpu_and_memory_only_resize=False):  # noqa C901
	filters = {"server_type": name, "legacy_plan": False}

	if cluster:
		filters.update({"cluster": cluster})

	# Removed default platform of x86_64;
	# Still use x86_64 for new database servers
	if platform:
		filters.update({"platform": platform})

	if resource_name:
		current_plan = frappe.db.get_value(name, resource_name, "plan")
		if current_plan:
			legacy_plan, platform = frappe.db.get_value(
				"Server Plan", current_plan, ["legacy_plan", "platform"]
			)
			filters.update({"legacy_plan": legacy_plan if platform == "x86_64" else False})

	current_root_disk_size = None
	if resource_name:
		resource_details = frappe.db.get_value(
			name, resource_name, ["virtual_machine", "provider"], as_dict=True
		)

		if resource_details.provider == "Hetzner" or resource_details.provider == "DigitalOcean":
			current_root_disk_size = (
				frappe.db.get_value("Virtual Machine", resource_details.virtual_machine, "root_disk_size")
				if resource_details and resource_details.virtual_machine
				else None
			)

			if current_root_disk_size is not None:
				# Hide all plans that offer less disk than current disk size
				filters.update({"disk": [">=", current_root_disk_size]})

	plans = Plan.get_plans(
		doctype="Server Plan",
		fields=[
			"name",
			"title",
			"price_usd",
			"price_inr",
			"vcpu",
			"memory",
			"disk",
			"cluster",
			"instance_type",
			"premium",
			"platform",
			"plan_type",
			"allow_unified_server",
			"machine_unavailable",
		],
		filters=filters,
	)

	default_server_plan_type = frappe.db.get_single_value("Press Settings", "default_server_plan_type")
	for plan in plans:
		if not plan.get("plan_type"):
			plan["plan_type"] = default_server_plan_type

		if (
			(frappe.session and frappe.session.data and frappe.session.data.user_type)
			or (
				frappe.session
				and frappe.session.user
				and frappe.get_cached_value("User", frappe.session.user, "user_type")
			)
		) == "System User":
			plan["allow_unified_server"] = plan.get("allow_unified_server", False)
		else:
			plan["allow_unified_server"] = frappe.local.team().allow_unified_servers and plan.get(
				"allow_unified_server", False
			)

	server_plan_types = get_server_plan_types()

	if cpu_and_memory_only_resize and current_root_disk_size is not None:
		# Show only CPU/memory upgrades by normalizing disk size
		for plan in plans:
			plan["disk"] = current_root_disk_size

	return {
		"plans": plans,
		"types": server_plan_types,
	}


@frappe.whitelist()
def play(play):
	play = frappe.get_doc("Ansible Play", play)
	play = play.as_dict()
	whitelisted_fields = [
		"name",
		"play",
		"creation",
		"status",
		"start",
		"end",
		"duration",
	]
	for key in list(play.keys()):
		if key not in whitelisted_fields:
			play.pop(key, None)

	play.steps = frappe.get_all(
		"Ansible Task",
		filters={"play": play.name},
		fields=["task", "status", "start", "end", "duration", "output"],
		order_by="creation",
	)
	return play


@frappe.whitelist()
@protected(["Server", "Database Server"])
def change_plan(name, plan):
	poly_get_doc(["Server", "Database Server"], name).change_plan(plan)


@frappe.whitelist()
@protected(["Server", "Database Server"])
def press_jobs(name):
	jobs = []
	for job in frappe.get_all("Press Job", {"server": name}, pluck="name"):
		jobs.append(frappe.get_doc("Press Job", job).detail())
	return jobs


@frappe.whitelist()
@protected(["Server", "Database Server"])
def jobs(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters=filters,
		start=limit_start,
		limit=limit_page_length,
		order_by=order_by or "creation desc",
	)

	for job in jobs:
		job["status"] = "Pending" if job["status"] == "Undelivered" else job["status"]

	return jobs


@frappe.whitelist()
@protected(["Server", "Database Server"])
def plays(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	return frappe.get_all(
		"Ansible Play",
		fields=["name", "play", "creation", "status", "start", "end", "duration"],
		filters=filters,
		start=limit_start,
		limit=limit_page_length,
		order_by=order_by or "creation desc",
	)


@frappe.whitelist()
@protected("Server")
def get_title_and_cluster(name):
	return frappe.db.get_value("Server", name, ["title", "cluster"], as_dict=True)


@frappe.whitelist()
@protected(["Server", "Database Server"])
def groups(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	if server.doctype == "Database Server":
		app_server = frappe.db.get_value("Server", {"database_server": server.name}, "name")
		server = frappe.get_doc("Server", app_server)

	return all_benches(server=server.name)


@frappe.whitelist()
@protected(["Server", "Database Server"])
def reboot(name):
	return poly_get_doc(["Server", "Database Server"], name).reboot()


@frappe.whitelist()
@protected(["Server", "Database Server"])
def rename(name, title):
	doc = poly_get_doc(["Server", "Database Server"], name)
	doc.title = title
	doc.save()


def get_timespan_timegrain(duration: str) -> tuple[int, int]:
	return TIMESPAN_TIMEGRAIN_MAP[duration]


@frappe.whitelist(allow_guest=True)
def benches_are_idle(server: str, access_token: str) -> None:
	"""Shut down the secondary server if all benches are idle.

	This function is only triggered by secondary servers:
	https://github.com/frappe/agent/pull/346/files#diff-7355d9c50cadfa3f4c74fc77a4ad8ab08e4da8f6c3326bbf9b0de0f00a0aa0daR87-R93
	"""
	from passlib.hash import pbkdf2_sha256 as pbkdf2

	server_doc = frappe.get_cached_doc("Server", server)
	agent_password = server_doc.get_password("agent_password")
	current_user = frappe.session.user

	if not pbkdf2.verify(agent_password, access_token):
		return

	primary_server, is_server_scaled_up = frappe.db.get_value(
		"Server", {"secondary_server": server}, ["name", "scaled_up"]
	)
	running_scale_down = frappe.db.get_value(
		"Auto Scale Record", {"secondary_server": server, "status": ("IN", ("Running", "Pending"))}
	)
	scaled_up_at = frappe.db.get_value(
		"Auto Scale Record", {"secondary_server": server, "scale_up": True}, "modified"
	)
	cool_off_period = frappe.db.get_single_value("Press Settings", "cool_off_period")

	should_scale_down = (
		not running_scale_down
		and is_server_scaled_up
		and scaled_up_at
		and (frappe.utils.now_datetime() - scaled_up_at) > timedelta(seconds=cool_off_period or 300)
	)
	if should_scale_down:
		# Scale down here
		frappe.set_user("Administrator")
		auto_scale_record: "AutoScaleRecord" = frappe.get_doc(
			{
				"doctype": "Auto Scale Record",
				"scale_up": False,
				"scale_down": True,
				"primary_server": primary_server,
			}
		)
		auto_scale_record.insert()
		frappe.set_user(current_user)


@frappe.whitelist()
@protected(["Server"])
def schedule_auto_scale(
	name, scheduled_scale_up_time: str | datetime, scheduled_scale_down_time: str | datetime
) -> None:
	"""Schedule two auto scale record with scale up and down actions at given times"""
	secondary_server = frappe.db.get_value("Server", name, "secondary_server")
	formatted_scheduled_scale_up_time = (
		datetime.strptime(scheduled_scale_up_time, "%Y-%m-%d %H:%M:%S")
		if isinstance(scheduled_scale_up_time, str)
		else scheduled_scale_up_time
	)
	formatted_scheduled_scale_down_time = (
		datetime.strptime(scheduled_scale_down_time, "%Y-%m-%d %H:%M:%S")
		if isinstance(scheduled_scale_down_time, str)
		else scheduled_scale_down_time
	)

	if (formatted_scheduled_scale_down_time - formatted_scheduled_scale_up_time).total_seconds() / 60 < 60:
		frappe.throw("Scheduled scales must be an hour apart", frappe.ValidationError)

	validate_scaling_schedule(
		name,
		formatted_scheduled_scale_up_time,
		formatted_scheduled_scale_down_time,
	)

	def create_record(action: str, scheduled_time: datetime) -> None:
		doc = frappe.get_doc(
			{
				"doctype": "Auto Scale Record",
				"action": action,
				"status": "Scheduled",
				"scheduled_time": scheduled_time,
				"primary_server": name,
				"secondary_server": secondary_server,
			}
		)
		doc.insert()

	create_record("Scale Up", formatted_scheduled_scale_up_time)
	create_record("Scale Down", formatted_scheduled_scale_down_time)


@frappe.whitelist()
@protected(["Server"])
def get_configured_autoscale_triggers(name) -> list[dict[str, float]] | None:
	return frappe.db.get_all(
		"Auto Scale Trigger",
		{"parent": name},
		["name", "metric", "threshold", "action"],
	)
