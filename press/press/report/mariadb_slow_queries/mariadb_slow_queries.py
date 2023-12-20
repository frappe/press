# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import re
from collections import defaultdict

import frappe
import requests
import sqlparse
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import convert_utc_to_timezone, get_system_timezone
from frappe.utils.password import get_decrypted_password


def execute(filters=None):
	frappe.only_for(["System Manager", "Site Manager"])
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

	if filters.normalize_queries:
		columns = [c for c in columns if c["fieldname"] not in ("timestamp",)]
		columns.append(
			{
				"fieldname": "count",
				"label": frappe._("Count"),
				"fieldtype": "Int",
			},
		)
		columns.append(
			{
				"fieldname": "example",
				"label": frappe._("Example Query"),
				"fieldtype": "Data",
				"width": 1200,
			},
		)

	data = get_data(filters)
	return columns, data


def get_data(filters):
	from press.utils import convert_user_timezone_to_utc

	rows = get_slow_query_logs(
		filters.database,
		convert_user_timezone_to_utc(filters.start_datetime),
		convert_user_timezone_to_utc(filters.stop_datetime),
		filters.search_pattern,
		int(filters.max_lines) or 100,
	)
	for row in rows:
		if filters.format_queries:
			row["query"] = format_query(row["query"])
		row["timestamp"] = convert_utc_to_timezone(
			frappe.utils.get_datetime(row["timestamp"]).replace(tzinfo=None),
			get_system_timezone(),
		)

	if filters.normalize_queries:
		return summarize_by_query(rows)

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

	if search_pattern and search_pattern != ".*":
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


def normalize_query(query: str) -> str:
	q = sqlparse.parse(query)[0]
	for token in q.flatten():
		token_type = str(token.ttype)
		if "Token.Literal" in token_type or token_type == "Token.Keyword.Order":
			token.value = "?"

	# Format query consistently so identical queries can be matched
	q = format_query(q, strip_comments=True)

	# Transform IN parts like this: IN (?, ?, ?) -> IN (?)
	q = re.sub(r" IN \(\?[\s\n\?\,]*\)", " IN (?)", q, flags=re.IGNORECASE)

	return q


def format_query(q, strip_comments=False):
	return sqlparse.format(
		str(q).strip(), keyword_case="upper", reindent=True, strip_comments=strip_comments
	)


def summarize_by_query(data):
	queries = defaultdict(lambda: defaultdict(float))
	for row in data:
		query = row["query"]
		if "SQL_NO_CACHE" in query and "WHERE" not in query:
			# These are mysqldump queries, there's no real way to optimize these, it's just dumping entire table.
			continue

		normalized_query = normalize_query(query)
		entry = queries[normalized_query]
		entry["count"] += 1
		entry["query"] = normalized_query
		entry["duration"] += row["duration"]
		entry["rows_examined"] += row["rows_examined"]
		entry["rows_sent"] += row["rows_sent"]
		entry["example"] = query

	result = list(queries.values())
	result.sort(key=lambda r: r["duration"] * r["count"], reverse=True)

	return result
