# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests

from press.utils import get_current_team
from press.api.site import protected
from frappe.utils import convert_utc_to_timezone
from frappe.utils.password import get_decrypted_password
from datetime import datetime


@frappe.whitelist()
def all():
	team = get_current_team()
	servers = frappe.get_all("Server", {"team": team}, ["name", "creation", "status"])
	database_servers = frappe.get_all(
		"Database Server", {"team": team}, ["name", "creation", "status"]
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
