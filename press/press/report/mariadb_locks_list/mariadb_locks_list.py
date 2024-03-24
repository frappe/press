# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.agent import Agent


def execute(filters=None):
	frappe.only_for("System Manager")
	data = get_data(filters)
	return get_columns(), data


def get_data(filters):
	server = frappe.get_doc("Database Server", filters.database_server)
	agent = Agent(server.name, "Database Server")

	data = {
		"private_ip": server.private_ip,
		"mariadb_root_password": server.get_password("mariadb_root_password"),
	}
	rows = agent.post("database/locks", data=data)
	return rows


def get_columns():

	return [
		{
			"fieldname": "lock_id",
			"label": "Lock ID",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "trx_id",
			"label": "Transaction ID",
			"fieldtype": "Data",
			"width": 70,
		},
		{
			"fieldname": "trx_query",
			"label": "Query",
			"fieldtype": "Data",
			"width": 500,
		},
		{
			"fieldname": "lock_mode",
			"label": "Lock Mode",
			"fieldtype": "Data",
			"width": 70,
		},
		{
			"fieldname": "lock_type",
			"label": "Lock Type",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "lock_table",
			"label": "Lock Table",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "lock_index",
			"label": "Lock Index",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "trx_state",
			"label": "Transaction State",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "trx_operation_state",
			"label": "Transaction Operation State",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "trx_started",
			"label": "Transaction Started At",
			"fieldtype": "Data",  # Avoid timezones, we only need to compare two txn
			"width": 150,
		},
		{
			"fieldname": "trx_rows_locked",
			"label": "Rows Locked",
			"fieldtype": "Int",
		},
		{
			"fieldname": "trx_rows_modified",
			"label": "Rows Modified",
			"fieldtype": "Int",
		},
	]
