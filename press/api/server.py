# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests

from press.utils import get_current_team, group_children_in_result
from press.api.site import protected
from frappe.utils import convert_utc_to_timezone
from frappe.utils.password import get_decrypted_password
from datetime import datetime


@frappe.whitelist()
def all():
	team = get_current_team()
	servers = frappe.get_all(
		"Server", {"team": team, "status": ("!=", "Archived")}, ["name", "creation", "status"]
	)
	database_servers = frappe.get_all(
		"Database Server",
		{"team": team, "status": ("!=", "Archived")},
		["name", "creation", "status"],
	)
	return servers + database_servers


@frappe.whitelist()
@protected("Server")
def get(name):
	server = frappe.get_doc("Server", name)
	return {
		"name": server.name,
		"status": server.status,
		"team": server.team,
		"region_info": frappe.db.get_value(
			"Cluster", server.cluster, ["title", "image"], as_dict=True
		),
	}


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
	machine = frappe.get_doc(
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
	db_server = machine.create_database_server()
	db_server.plan = db_plan.name
	db_server.save()
	db_server.create_subscription(db_plan.name)

	app_plan = frappe.get_doc("Plan", server["app_plan"])
	machine = frappe.get_doc(
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
	app_server = machine.create_server()
	app_server.plan = app_plan.name
	app_server.save()
	app_server.create_subscription(app_plan.name)

	return {"server": app_server.name}


@frappe.whitelist()
def search_list():
	servers = frappe.get_list(
		"Server",
		fields=["name"],
		filters={"status": ("!=", "Archived"), "team": get_current_team()},
		order_by="creation desc",
	)
	database_servers = frappe.get_list(
		"Database Server",
		fields=["name"],
		filters={"status": ("!=", "Archived"), "team": get_current_team()},
		order_by="creation desc",
	)
	return servers + database_servers


@frappe.whitelist()
@protected("Server")
def analytics(name, query, timezone, duration="7d"):
	timespan, timegrain = {
		"1h": (60 * 60, 2 * 60),
		"6h": (6 * 60 * 60, 5 * 60),
		"24h": (24 * 60 * 60, 30 * 60),
		"7d": (7 * 24 * 60 * 60, 3 * 60 * 60),
		"15d": (15 * 24 * 60 * 60, 6 * 60 * 60),
	}[duration]

	query_map = {
		"cpu": f"""sum by (mode)(rate(node_cpu_seconds_total{{instance="{name}", job="node"}}[{timegrain}s])) * 100""",
		"network": f"""rate(node_network_receive_bytes_total{{instance="{name}", job="node"}}[{timegrain}s]) * 8""",
		"iops": f"""rate(node_disk_reads_completed_total{{instance="{name}", job="node"}}[{timegrain}s])""",
		"space": f"""100 - ((node_filesystem_avail_bytes{{instance="{name}", job="node"}} * 100) / node_filesystem_size_bytes{{instance="{name}", job="node"}})""",
		"loadavg": f"""{{__name__=~"node_load1|node_load5|node_load15", instance="{name}", job="node"}}""",
	}

	return prometheus_query(query_map[query], timezone, timespan, timegrain)


def prometheus_query(query, timezone, timespan, timegrain):
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return []

	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")

	end = frappe.utils.now_datetime()
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

	for timestamp, _ in response["data"]["result"][0]["values"]:
		labels.append(
			convert_utc_to_timezone(
				datetime.fromtimestamp(timestamp).replace(tzinfo=None), timezone
			)
		)

	for index in range(len(response["data"]["result"])):
		dataset = {"name": str(response["data"]["result"][index]["metric"]), "values": []}
		for _, value in response["data"]["result"][index]["values"]:
			dataset["values"].append(float(value))
		datasets.append(dataset)

	return {"datasets": datasets, "labels": labels}


@frappe.whitelist()
def options():
	regions = frappe.get_all(
		"Cluster", {"cloud_provider": "AWS EC2", "public": True}, ["name", "title", "image"]
	)
	return {
		"regions": regions * 2,
		"app_plans": plans("Server"),
		"db_plans": plans("Database Server"),
	}


def plans(name):
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
		filters={"enabled": True, "document_type": name},
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
@protected("Server")
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
@protected("Server")
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
