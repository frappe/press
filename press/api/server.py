# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.utils import get_current_team
from press.api.site import protected


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
