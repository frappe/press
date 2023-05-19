# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
import pytz
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import convert_utc_to_timezone, get_datetime, get_system_timezone

from press.agent import Agent

COLUMNS = [
	{
		"fieldname": "timestamp",
		"label": "Timestamp",
		"fieldtype": "Datetime",
		"width": 160,
	},
	{
		"fieldname": "query",
		"label": "Query",
		"fieldtype": "Data",
		"width": 1200,
	},
]


def execute(filters=None):
	frappe.only_for("System Manager")
	filters.database = frappe.db.get_value("Site", filters.site, "database_name")

	make_access_log(
		doctype="Site",
		document=filters.site,
		file_type="MariaDB Deadlock Browser",
		report_name="MariaDB Deadlock Browser",
		filters=filters,
	)
	data = get_data(filters)
	return COLUMNS, data


def convert_user_timezone_to_utc(datetime_obj):
	timezone = pytz.timezone(get_time_zone())
	datetime_obj = get_datetime(datetime_obj)
	return timezone.localize(datetime_obj).astimezone(pytz.utc).isoformat()


def get_data(filters):
	application_server = frappe.db.get_value("Site", filters.site, "server")
	database_server_name = frappe.db.get_value(
		"Server", application_server, "database_server"
	)

	database_server = frappe.get_doc("Database Server", database_server_name)

	agent = Agent(database_server.name, "Database Server")

	data = {
		"private_ip": database_server.private_ip,
		"mariadb_root_password": database_server.get_password("mariadb_root_password"),
		"database": filters.database,
		"start_datetime": convert_user_timezone_to_utc(filters.start_datetime),
		"stop_datetime": convert_user_timezone_to_utc(filters.stop_datetime),
		"max_lines": filters.max_lines or 1000,
	}

	results = agent.post(f"database/deadlocks", data=data)

	return post_process(results)


def post_process(rows):
	results = []

	for idx, row in enumerate(rows):
		row["timestamp"] = convert_utc_to_timezone(
			frappe.utils.get_datetime(row["ts"]).replace(tzinfo=None), get_time_zone()
		)
		results.append(row)

		# Two sequential queries are part of same "deadlock", so add empty line for readability
		if idx % 2:
			results.append({})

	return results


"""
Deadlock table schema

+-----------+----------------------+------+-----+---------------------+-------+
| Field     | Type                 | Null | Key | Default             | Extra |
+-----------+----------------------+------+-----+---------------------+-------+
| ts        | timestamp            | NO   | PRI | current_timestamp() |       |
| user      | char(16)             | NO   |     | NULL                |       |
| query     | text                 | NO   |     | NULL                |       |
| victim    | tinyint(3) unsigned  | NO   |     | NULL                |       |
| idx       | char(64)             | NO   |     | NULL                |       |
| lock_type | char(16)             | NO   |     | NULL                |       |
| lock_mode | char(1)              | NO   |     | NULL                |       |
| server    | char(20)             | NO   | PRI | NULL                |       |
| thread    | int(10) unsigned     | NO   | PRI | NULL                |       |
| txn_id    | bigint(20) unsigned  | NO   |     | NULL                |       |
| txn_time  | smallint(5) unsigned | NO   |     | NULL                |       |
| hostname  | char(20)             | NO   |     | NULL                |       |
| ip        | char(15)             | NO   |     | NULL                |       |
| db        | char(64)             | NO   |     | NULL                |       |
| tbl       | char(64)             | NO   |     | NULL                |       |
| wait_hold | char(1)              | NO   |     | NULL                |       |
+-----------+----------------------+------+-----+---------------------+-------+
"""
