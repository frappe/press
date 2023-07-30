# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import pytz
import sqlparse
from press.agent import Agent
from frappe.utils import (
	get_datetime,
	get_datetime_str,
	get_system_timezone,
)
from frappe.core.doctype.access_log.access_log import make_access_log

try:
	from frappe.utils import convert_utc_to_user_timezone
except ImportError:
	from frappe.utils import convert_utc_to_system_timezone as convert_utc_to_user_timezone


def execute(filters=None):
	frappe.only_for(["System Manager", "Site Manager"])
	filters.database = frappe.get_doc("Site", filters.site).fetch_info()["config"][
		"db_name"
	]

	make_access_log(
		doctype="Site",
		document=filters.site,
		file_type="Binary Log",
		report_name="Binary Log Browser",
		filters=filters,
	)

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


def get_data(filters):
	server = frappe.db.get_value("Site", filters.site, "server")
	database_server = frappe.db.get_value("Server", server, "database_server")
	agent = Agent(database_server, "Database Server")

	data = {
		"database": filters.database,
		"start_datetime": convert_user_timezone_to_utc(filters.start_datetime),
		"stop_datetime": convert_user_timezone_to_utc(filters.stop_datetime),
		"search_pattern": filters.pattern,
		"max_lines": filters.max_lines or 4000,
	}

	files = agent.get("database/binary/logs")

	files_in_timespan = get_files_in_timespan(
		files, data["start_datetime"], data["stop_datetime"]
	)

	results = []
	for file in files_in_timespan:
		rows = agent.post(f"database/binary/logs/{file}", data=data)
		for row in rows:
			if filters.format_queries:
				row["query"] = sqlparse.format(
					row["query"].strip(), keyword_case="upper", reindent=True
				)
			row["timestamp"] = get_datetime_str(
				convert_utc_to_user_timezone(get_datetime(row["timestamp"]))
			)
			results.append(row)

			if len(results) > data["max_lines"]:
				return results

	return results


def get_files_in_timespan(
	files: list[dict[str, str]], start: str, stop: str
) -> list[str]:
	files.sort(key=lambda f: f["modified"])

	files_in_timespan = []

	for file in files:
		if file["modified"] > stop:
			# This is last file that captures timespan
			# Include it and dont process any further.
			files_in_timespan.append(file["name"])
			break

		if start > file["modified"]:
			# Modified timestamp is *usually* last time when log file was touched,
			# i.e. last query logged on file
			continue

		files_in_timespan.append(file["name"])

	return files_in_timespan


def convert_user_timezone_to_utc(datetime):
	timezone = pytz.timezone(get_system_timezone())
	datetime = get_datetime(datetime)
	return get_datetime_str(timezone.localize(datetime).astimezone(pytz.utc))
