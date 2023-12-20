# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import re
from collections import defaultdict
from dataclasses import dataclass
import requests
import sqlparse

import frappe
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils.caching import redis_cache
from frappe.utils import convert_utc_to_timezone, get_system_timezone
from frappe.utils.password import get_decrypted_password

from press.api.site import protected
from press.agent import Agent
from press.press.report.mariadb_slow_queries.db_optimizer import (
	ColumnStat,
	DBExplain,
	DBIndex,
	DBOptimizer,
	DBTable,
)


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

	if filters.analyze:
		columns.append(
			{
				"fieldname": "suggested_index",
				"label": frappe._("Suggest Index"),
				"fieldtype": "Data",
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
		rows = summarize_by_query(rows)

	if filters.analyze:
		rows = analyze_queries(rows, filters.site)

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


def analyze_queries(data, site):
	# TODO: handle old framework and old agents and general failures
	for row in data:
		analyzer = OptimizeDatabaseQuery(site, row["example"])
		if index := analyzer.analyze():
			row["suggested_index"] = f"{index.table}.{index.column}"
	return data


@frappe.whitelist()
@protected("Site")
def add_suggested_index(name: str, index: str):
	frappe.enqueue(_add_suggested_index, index=index, site_name=name)


def _add_suggested_index(site_name, index):
	if not index:
		frappe.throw("No index suggested")

	table, column = index.split(".")
	doctype = get_doctype_name(table)

	site = frappe.get_cached_doc("Site", site_name)
	agent = Agent(site.server)
	agent.add_database_index(site, doctype=doctype, columns=[column])
	frappe.msgprint(f"Index {index} added on site {site_name} successfully", realtime=True)


@dataclass
class OptimizeDatabaseQuery:
	site: str
	query: str

	def analyze(self) -> DBIndex | None:
		explain_output = self.fetch_explain()

		explain_output = [DBExplain.from_frappe_ouput(e) for e in explain_output]
		optimizer = DBOptimizer(query=self.query, explain_output=explain_output)
		tables = optimizer.tables_examined

		for table in tables:
			stats = _fetch_table_stats(self.site, table)
			db_table = DBTable.from_frappe_ouput(stats)
			column_stats = _fetch_column_stats(self.site, table)
			db_table.update_cardinality(column_stats)
			optimizer.update_table_data(db_table)

		return optimizer.suggest_index()

	def fetch_explain(self) -> list[dict]:
		site = frappe.get_cached_doc("Site", self.site)
		db_server_name = frappe.db.get_value("Server", site.server, "database_server")
		database_server = frappe.get_cached_doc("Database Server", db_server_name)
		agent = Agent(database_server.name, "Database Server")

		data = {
			"schema": site.database_name,
			"query": self.query,
			"private_ip": database_server.private_ip,
			"mariadb_root_password": database_server.get_password("mariadb_root_password"),
		}

		return agent.post("database/explain", data=data)


@redis_cache(ttl=60 * 5)
def _fetch_table_stats(site: str, table: str):
	site = frappe.get_cached_doc("Site", site)
	agent = Agent(site.server)
	return agent.describe_database_table(
		site,
		doctype=get_doctype_name(table),
		columns=[],
	)


@redis_cache(ttl=60 * 5)
def _fetch_column_stats(site, table):
	site = frappe.get_cached_doc("Site", site)
	db_server_name = frappe.db.get_value(
		"Server", site.server, "database_server", cache=True
	)
	database_server = frappe.get_cached_doc("Database Server", db_server_name)
	agent = Agent(database_server.name, "Database Server")

	data = {
		"schema": site.database_name,
		"table": table,
		"private_ip": database_server.private_ip,
		"mariadb_root_password": database_server.get_password("mariadb_root_password"),
	}

	column_stats = agent.post("database/column-stats", data=data)
	return [ColumnStat.from_frappe_ouput(c) for c in column_stats]


def get_doctype_name(table_name: str) -> str:
	return table_name.removeprefix("tab")
