# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests

from press.utils import get_current_team, group_children_in_result
from press.api.site import protected
from press.api.bench import all as all_benches
from frappe.utils import convert_utc_to_timezone
from frappe.utils.password import get_decrypted_password
from datetime import datetime, timezone as tz
from frappe.utils import flt


def poly_get_doc(doctypes, name):
	for doctype in doctypes:
		if frappe.db.exists(doctype, name):
			return frappe.get_doc(doctype, name)
	return frappe.get_doc(doctypes[-1], name)


@frappe.whitelist()
def all():
	team = get_current_team()
	app_servers = frappe.get_all(
		"Server",
		{"team": team, "status": ("!=", "Archived")},
		["name", "creation", "status", "title"],
	)
	database_servers = frappe.get_all(
		"Database Server",
		{"team": team, "status": ("!=", "Archived")},
		["name", "creation", "status", "title"],
	)
	all_servers = app_servers + database_servers
	for server in all_servers:
		server["app_server"] = f"f{server.name[1:]}"
	return all_servers


@frappe.whitelist()
@protected(["Server", "Database Server"])
def get(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	return {
		"name": server.name,
		"title": server.title,
		"status": server.status,
		"team": server.team,
		"app_server": f"f{server.name[1:]}",
		"region_info": frappe.db.get_value(
			"Cluster", server.cluster, ["name", "title", "image"], as_dict=True
		),
	}


@frappe.whitelist()
@protected(["Server", "Database Server"])
def overview(name):
	server = poly_get_doc(["Server", "Database Server"], name)
	return {
		"plan": frappe.get_doc("Plan", server.plan).as_dict(),
		"info": {
			"owner": frappe.db.get_value(
				"User",
				server.team,
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
	if server.doctype == "Database Server":
		app_server_name = frappe.db.get_value(
			"Server", {"database_server": server.name}, "name"
		)
		app_server = frappe.get_doc("Server", app_server_name)
		db_server = server
	else:
		app_server = server
		db_server = frappe.get_doc("Database Server", server.database_server)
	app_server.archive()
	db_server.archive()


@frappe.whitelist()
def new(server):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")

	domain = frappe.db.get_single_value("Press Settings", "domain")
	cluster = server["cluster"]

	app_image = db_image = None
	db_images = frappe.get_all(
		"Virtual Machine Image",
		{"status": "Available", "series": "m", "cluster": cluster},
		pluck="name",
	)
	if db_images:
		db_image = db_images[0]

	app_images = frappe.get_all(
		"Virtual Machine Image",
		{"status": "Available", "series": "f", "cluster": cluster},
		pluck="name",
	)
	if app_images:
		app_image = app_images[0]

	db_plan = frappe.get_doc("Plan", server["db_plan"])
	db_machine = frappe.get_doc(
		{
			"doctype": "Virtual Machine",
			"cluster": cluster,
			"domain": domain,
			"series": "m",
			"disk_size": db_plan.disk,
			"machine_type": db_plan.instance_type,
			"virtual_machine_image": db_image,
			"team": team.name,
		}
	).insert()
	db_server = db_machine.create_database_server()
	db_server.plan = db_plan.name
	db_server.title = f"{server['title']} - Database"
	db_server.save()
	db_server.create_subscription(db_plan.name)
	db_server.run_press_job("Create Server")

	proxy_server = frappe.get_all(
		"Proxy Server", {"status": "Active", "cluster": cluster}, limit=1
	)[0]

	app_plan = frappe.get_doc("Plan", server["app_plan"])
	app_machine = frappe.get_doc(
		{
			"doctype": "Virtual Machine",
			"cluster": cluster,
			"domain": domain,
			"series": "f",
			"disk_size": app_plan.disk,
			"machine_type": app_plan.instance_type,
			"virtual_machine_image": app_image,
			"team": team.name,
		}
	).insert()
	app_server = app_machine.create_server()
	app_server.plan = app_plan.name
	app_server.ram = app_plan.memory
	app_server.new_worker_allocation = True
	app_server.database_server = db_server.name
	app_server.proxy_server = proxy_server.name
	app_server.title = f"{server['title']} - Application"
	app_server.save()
	app_server.create_subscription(app_plan.name)

	job = app_server.run_press_job("Create Server")

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
		"Cluster", {"cloud_provider": "AWS EC2", "public": True}, ["name", "title", "image"]
	)
	return {
		"regions": regions,
		"app_plans": plans("Server"),
		"db_plans": plans("Database Server"),
	}


@frappe.whitelist()
def plans(name, cluster=None):
	filters = {"enabled": True, "document_type": name}
	if cluster:
		filters["cluster"] = cluster
	plans = frappe.db.get_all(
		"Plan",
		fields=[
			"name",
			"plan_title",
			"price_usd",
			"price_inr",
			"vcpu",
			"memory",
			"disk",
			"cluster",
			"instance_type",
			"`tabHas Role`.role",
		],
		filters=filters,
		order_by="price_usd asc",
	)
	plans = group_children_in_result(plans, {"role": "roles"})

	out = []
	for plan in plans:
		if frappe.utils.has_common(plan["roles"], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)
	return out


@frappe.whitelist()
@protected(["Server", "Database Server"])
def jobs(name, start=0):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"server": name},
		start=start,
		limit=10,
	)
	return jobs


@frappe.whitelist()
@protected(["Server", "Database Server"])
def plays(name, start=0):
	plays = frappe.get_all(
		"Ansible Play",
		fields=["name", "play", "creation", "status", "start", "end", "duration"],
		filters={"server": name},
		start=start,
		limit=10,
	)
	return plays


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
