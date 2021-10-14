# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import pytz
import sqlparse
from press.agent import Agent
from frappe.utils import get_datetime, convert_utc_to_user_timezone, get_datetime_str


def execute(filters=None):
	frappe.only_for("System Manager")
	filters.database = frappe.get_doc("Site", filters.site).fetch_info()["config"][
		"db_name"
	]
	data = get_data(filters)

	columns = [
		{
			"fieldname": "timestamp",
			"label": frappe._("Timestamp"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "query",
			"label": frappe._("Query"),
			"fieldtype": "Data",
			"width": 1200,
		},
	]
	return columns, data


@frappe.whitelist()
def get_files(*args, **kwargs):
	def get_size(size):
		if size > 1048576:
			return "{0:.1f} MB".format(float(size) / 1048576)
		else:
			return "{0:.1f} KB".format(float(size) / 1024)

	frappe.only_for("System Manager")

	site = args[-1]["site"]

	server = frappe.db.get_value("Site", site, "server")
	database_server = frappe.db.get_value("Server", server, "database_server")
	agent = Agent(database_server, "Database Server")

	files = []
	for file in agent.get("database/binary/logs"):
		size = file["size"]
		modified = convert_utc_to_user_timezone(get_datetime(file["modified"]))
		files.append([file["name"], modified, get_size(size)])
	return sorted(files)


def get_data(filters):
	server = frappe.db.get_value("Site", filters.site, "server")
	database_server = frappe.db.get_value("Server", server, "database_server")
	agent = Agent(database_server, "Database Server")

	data = {
		"database": filters.database,
		"start_datetime": get_datetime_str(
			get_datetime(filters.start_datetime).astimezone(pytz.utc)
		),
		"stop_datetime": get_datetime_str(
			get_datetime(filters.stop_datetime).astimezone(pytz.utc)
		),
		"search_pattern": filters.pattern,
		"max_lines": filters.max_lines or 4000,
	}
	rows = agent.post(f"database/binary/logs/{filters.file}", data=data)
	for row in rows:
		row["query"] = sqlparse.format(row["query"].strip(), keyword_case="upper", reindent=True)
		row["timestamp"] = get_datetime_str(
			convert_utc_to_user_timezone(get_datetime(row["timestamp"]))
		)
	return rows
