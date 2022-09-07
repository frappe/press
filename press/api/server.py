# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.utils import get_current_team


@frappe.whitelist()
def all():
	team = get_current_team()
	servers = frappe.get_all("Server", {"team": team}, ["name", "creation", "status"])
	database_servers = frappe.get_all("Database Server", {"team": team}, ["name", "creation", "status"])
	return servers + database_servers
