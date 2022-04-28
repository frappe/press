# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

import sqlparse
from press.agent import Agent
from frappe.utils import cint


def execute(filters=None):
	frappe.only_for("System Manager")

	columns = [
		{
			"fieldname": "Id",
			"label": frappe._("ID"),
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"fieldname": "User",
			"label": frappe._("User"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "Host",
			"label": frappe._("Host"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "db",
			"label": frappe._("Database"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "Command",
			"label": frappe._("Command"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "Time",
			"label": frappe._("Time"),
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"fieldname": "State",
			"label": frappe._("State"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "Info",
			"label": frappe._("Info"),
			"fieldtype": "Data",
			"width": 400,
		},
		{
			"fieldname": "Progress",
			"label": frappe._("Progress"),
			"fieldtype": "Float",
			"width": 80,
		},
	]

	data = get_data(filters)
	return columns, data


def get_data(filters):
	server = frappe.get_doc("Database Server", filters.database_server)
	agent = Agent(server.name, "Database Server")

	data = {
		"private_ip": server.private_ip,
		"mariadb_root_password": server.get_password("mariadb_root_password"),
	}
	rows = agent.post("database/processes", data=data)

	for row in rows:
		row["Info"] = sqlparse.format(
			(row.get["Info"] or "").strip(), keyword_case="upper", reindent=True
		)
	return rows


@frappe.whitelist()
def kill(database_server, kill_threshold):
	frappe.only_for("System Manager")
	server = frappe.get_doc("Database Server", database_server)
	agent = Agent(server.name, "Database Server")

	data = {
		"private_ip": server.private_ip,
		"mariadb_root_password": server.get_password("mariadb_root_password"),
		"kill_threshold": cint(kill_threshold),
	}
	agent.post("database/processes/kill", data=data)
