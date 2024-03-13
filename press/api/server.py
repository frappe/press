# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests
from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.site_plan.plan import Plan

from press.utils import get_current_team
from press.api.site import protected
from press.api.bench import all as all_benches
from frappe.utils import convert_utc_to_timezone
from frappe.utils.password import get_decrypted_password
from datetime import datetime, timezone as tz
from frappe.utils import flt
from press.press.doctype.team.team import get_child_team_members


def poly_get_doc(doctypes, name):
	for doctype in doctypes:
		if frappe.db.exists(doctype, name):
			return frappe.get_doc(doctype, name)
	return frappe.get_doc(doctypes[-1], name)


@frappe.whitelist()
def all(server_filter=None):
	if server_filter is None:
		server_filter = {"server_type": "", "tag": ""}

	team = get_current_team()
	child_teams = [team.name for team in get_child_team_members(team)]
	teams = [team] + child_teams

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
		server["plan"] = (
			frappe.get_doc("Server Plan", server_plan_name) if server_plan_name else None
		)
		server["app_server"] = f"f{server.name[1:]}"
		server["tags"] = frappe.get_all(
			"Resource Tag", {"parent": server.name}, pluck="tag_name"
		)
		server["region_info"] = frappe.db.get_value(
			"Cluster", server.cluster, ["title", "image"], as_dict=True
		)
	return servers


@frappe.whitelist()
def server_tags():
	team = get_current_team()
	return frappe.get_all(
		"Press Tag", {"team": team, "doctype_name": "Server"}, pluck="tag"
	)


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
		"tags": frappe.get_all(
			"Press Tag", {"team": server.team, "doctype_name": "Server"}, ["name", "tag"]
		),
		"type": "database-server" if server.meta.name == "Database Server" else "server",
	}


@frappe.whitelist()
@protected(["Server", "Database Server"])
def overview(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	plan = frappe.get_doc("Server Plan", server.plan) if server.plan else None

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
def new(server):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")

	cluster: Cluster = frappe.get_doc("Cluster", server["cluster"])

	db_plan = frappe.get_doc("Server Plan", server["db_plan"])
	db_server, job = cluster.create_server(
		"Database Server", server["title"], db_plan, team=team.name
	)

	proxy_server = frappe.get_all(
		"Proxy Server", {"status": "Active", "cluster": cluster.name}, limit=1
	)[0]

	# to be used by app server
	cluster.database_server = db_server.name
	cluster.proxy_server = proxy_server.name

	app_plan = frappe.get_doc("Server Plan", server["app_plan"])
	app_server, job = cluster.create_server(
		"Server", server["title"], app_plan, team=team.name
	)

	return {"server": app_server.name, "job": job.name}


@frappe.whitelist()
@protected(["Server", "Database Server"])
def usage(name):
	query_map = {
		"vcpu": (
			f"""((count(count(node_cpu_seconds_total{{instance="{name}",job="node"}}) by (cpu))) - avg(sum by (mode)(rate(node_cpu_seconds_total{{mode='idle',instance="{name}",job="node"}}[120s])))) / count(count(node_cpu_seconds_total{{instance="{name}",job="node"}}) by (cpu))""",
			lambda x: x,
		),
		"disk": (
			f"""(node_filesystem_size_bytes{{instance="{name}", job="node", mountpoint="/"}} - node_filesystem_avail_bytes{{instance="{name}", job="node", mountpoint="/"}}) / (1024 * 1024 * 1024)""",
			lambda x: x,
		),
		"memory": (
			f"""(node_memory_MemTotal_bytes{{instance="{name}",job="node"}} - node_memory_MemFree_bytes{{instance="{name}",job="node"}} - (node_memory_Cached_bytes{{instance="{name}",job="node"}} + node_memory_Buffers_bytes{{instance="{name}",job="node"}})) / (1024 * 1024)""",
			lambda x: x,
		),
	}

	result = {}
	for usage_type, query in query_map.items():
		response = prometheus_query(query[0], query[1], "Asia/Kolkata", 120, 120)["datasets"]
		if response:
			result[usage_type] = response[0]["values"][-1]
	return result


@protected(["Server", "Database Server"])
def total_resource(name):
	query_map = {
		"vcpu": (
			f"""(count(count(node_cpu_seconds_total{{instance="{name}",job="node"}}) by (cpu)))""",
			lambda x: x,
		),
		"disk": (
			f"""(node_filesystem_size_bytes{{instance="{name}", job="node", mountpoint="/"}}) / (1024 * 1024 * 1024)""",
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
def analytics(name, query, timezone, duration):
	timespan, timegrain = {
		"1 Hour": (60 * 60, 2 * 60),
		"6 Hour": (6 * 60 * 60, 5 * 60),
		"24 Hour": (24 * 60 * 60, 30 * 60),
		"7 Days": (7 * 24 * 60 * 60, 3 * 60 * 60),
		"15 Days": (15 * 24 * 60 * 60, 6 * 60 * 60),
	}[duration]

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
			f"""100 - ((node_filesystem_avail_bytes{{instance="{name}", job="node", device="/dev/root"}} * 100) / node_filesystem_size_bytes{{instance="{name}", job="node", device="/dev/root"}})""",
			lambda x: x["device"],
		),
		"loadavg": (
			f"""{{__name__=~"node_load1|node_load5|node_load15", instance="{name}", job="node"}}""",
			lambda x: f"Load Average {x['__name__'][9:]}",
		),
		"memory": (
			f"""node_memory_MemTotal_bytes{{instance="{name}",job="node"}} - node_memory_MemFree_bytes{{instance="{name}",job="node"}} - (node_memory_Cached_bytes{{instance="{name}",job="node"}} + node_memory_Buffers_bytes{{instance="{name}",job="node"}})""",
			lambda x: "Used",
		),
	}

	return prometheus_query(
		query_map[query][0], query_map[query][1], timezone, timespan, timegrain
	)


def prometheus_query(query, function, timezone, timespan, timegrain):
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return []

	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")

	end = datetime.utcnow().replace(tzinfo=tz.utc)
	start = frappe.utils.add_to_date(end, seconds=-timespan)
	query = {
		"query": query,
		"start": start.timestamp(),
		"end": end.timestamp(),
		"step": f"{timegrain}s",
	}

	response = requests.get(url, params=query, auth=("frappe", password)).json()

	datasets = []
	labels = []

	if not response["data"]["result"]:
		return {"datasets": datasets, "labels": labels}

	for timestamp, _ in response["data"]["result"][0]["values"]:
		labels.append(
			convert_utc_to_timezone(
				datetime.fromtimestamp(timestamp, tz=tz.utc).replace(tzinfo=None), timezone
			)
		)

	for index in range(len(response["data"]["result"])):
		dataset = {
			"name": function(response["data"]["result"][index]["metric"]),
			"values": [],
		}
		for _, value in response["data"]["result"][index]["values"]:
			dataset["values"].append(flt(value, 2))
		datasets.append(dataset)

	return {"datasets": datasets, "labels": labels}


@frappe.whitelist()
def options():
	if not get_current_team(get_doc=True).servers_enabled:
		frappe.throw("Servers feature is not yet enabled on your account")
	regions = frappe.get_all(
		"Cluster",
		{"cloud_provider": ("!=", "Generic"), "public": True},
		["name", "title", "image", "beta"],
	)
	return {
		"regions": regions,
		"app_plans": plans("Server"),
		"db_plans": plans("Database Server"),
	}


@frappe.whitelist()
def plans(name, cluster=None):
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
		],
		filters={"server_type": name, "cluster": cluster}
		if cluster
		else {"server_type": name},
	)

	return plans


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
	plays = frappe.get_all(
		"Ansible Play",
		fields=["name", "play", "creation", "status", "start", "end", "duration"],
		filters=filters,
		start=limit_start,
		limit=limit_page_length,
		order_by=order_by or "creation desc",
	)
	return plays


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
