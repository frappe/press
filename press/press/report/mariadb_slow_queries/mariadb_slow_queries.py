# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import pytz
import requests
import sqlparse

from frappe.utils import (
	get_datetime,
	convert_utc_to_timezone,
	get_system_timezone,
)
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils.password import get_decrypted_password


def execute(filters=None):
	frappe.only_for("System Manager")
	filters.database = frappe.db.get_value("Site", filters.site, "database_name")

	make_access_log(
		doctype="Site",
		document=filters.site,
		file_type="MariaDB Slow Query",
		report_name="MariaDB Slow Queries",
		filters=filters,
	)

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
		{
			"fieldname": "duration",
			"label": frappe._("Duration"),
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"fieldname": "rows_examined",
			"label": frappe._("Rows Examined"),
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"fieldname": "rows_sent",
			"label": frappe._("Rows Sent"),
			"fieldtype": "Int",
			"width": 140,
		},
	]

	data = get_data(filters)
	return columns, data


def get_data(filters):
	def convert_user_timezone_to_utc(datetime_obj):
		timezone = pytz.timezone(get_system_timezone())
		datetime_obj = get_datetime(datetime_obj)
		return timezone.localize(datetime_obj).astimezone(pytz.utc).isoformat()

	rows = get_slow_query_logs(
		filters.database,
		convert_user_timezone_to_utc(filters.start_datetime),
		convert_user_timezone_to_utc(filters.end_datetime),
		filters.search_pattern,
		int(filters.max_lines) or 100,
	)
	for row in rows:
		if filters.format_queries:
			row["query"] = sqlparse.format(
				row["query"].strip(), keyword_case="upper", reindent=True
			)
		row["timestamp"] = convert_utc_to_timezone(
			frappe.utils.get_datetime(row["timestamp"]).replace(tzinfo=None),
			get_system_timezone(),
		)
	return rows


def get_slow_query_logs(database, start_datetime, end_datetime, search_pattern, size):
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return []

	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	query = {
		"query": {
			"bool": {
				"filter": [
					{"exists": {"field": "mysql.slowlog.query"}},
					{"match_phrase": {"mysql.slowlog.schema": database}},
					{"range": {"@timestamp": {"gt": start_datetime, "lte": end_datetime}}},
				],
			}
		},
		"size": size,
	}

	if search_pattern:
		query["query"]["bool"]["filter"].append(
			{"regexp": {"mysql.slowlog.query": search_pattern}}
		)

	response = requests.post(url, json=query, auth=("frappe", password)).json()

	out = []
	for d in response["hits"]["hits"]:
		data = d["_source"]["mysql"]["slowlog"]
		data["timestamp"] = d["_source"]["@timestamp"]
		data["duration"] = d["_source"].get("event", {}).get("duration", 0) / 1e9
		out.append(data)
	return out
