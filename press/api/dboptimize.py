import json
from typing import TYPE_CHECKING

import frappe
from press.agent import Agent

from press.api.site import protected

from press.press.report.mariadb_slow_queries.mariadb_slow_queries import (
	OptimizeDatabaseQuery,
	_fetch_column_stats,
	_fetch_table_stats,
)
from press.press.report.mariadb_slow_queries.db_optimizer import (
	ColumnStat,
	DBExplain,
	DBIndex,
	DBOptimizer,
	DBTable,
)


@frappe.whitelist()
@protected("Site")
def mariadb_analyze_query(name, row):
	suggested_index = analyze_query(row=row, site=name)
	return suggested_index


def analyze_query(row, site):
	query = row["example"]
	if not query.lower().startswith(("select", "update", "delete")):
		return
	analyzer = OptimizeDatabaseQuery(site, query)
	explain_output = analyzer.fetch_explain() or []
	explain_output = [DBExplain.from_frappe_ouput(e) for e in explain_output]
	optimizer = DBOptimizer(query=analyzer.query, explain_plan=explain_output)
	tables = optimizer.tables_examined
	doc = frappe.get_doc(
		{
			"doctype": "MariaDB Analyze Query",
			"site": site,
			"query": query,
			"tables_in_query": [],
		}
	)
	doc.insert()
	# for table_name in tables:
	#     doc.append("tables_in_query", {"table": table_name})
	for table in tables:
		stats = _fetch_table_stats(analyzer.site, table)
		doc.append("tables_in_query", {"table": table, "table_statistics": json.dumps(stats)})
		if not stats:
			# Old framework version
			return
		db_table = DBTable.from_frappe_ouput(stats)
		column_stats = _fetch_column_stats(analyzer.site, table, doc.get_title())
	# if index := analyzer.analyze():
	#     row["suggested_index"] = f"{index.table}.{index.column}"
	doc.save()
	return tables


def fetch_column_stats_update(job, response_data):
	if job.status == "Success":
		doc_name = response_data["data"]["doc_name"]
		column_statistics = response_data["steps"][0]["data"]["output"]
		table = job.request_data["table"]
		doc = frappe.get_doc("MariaDB Analyze Query", doc_name)
		for item in doc.tables_in_query:
			if item.table == table:
				item.column_statistics = json.dumps(column_statistics)
				doc.save()


# @frappe.whitelist()
# def test_job_for_column_stats():

# 	database_server = frappe.get_cached_doc("Database Server", "m1.arun.fc.frappe.dev")
# 	agent = Agent(database_server.name, "Database Server")
# 	data = {
# 		"schema": "_00fb2ab8304e8635",
# 		"table": "tabUser",
# 		"private_ip": "10.12.0.3",
# 		"mariadb_root_password": database_server.get_password("mariadb_root_password"),
# 	}
# 	column_stats = agent.create_agent_job(
# 		"Column Statistics", f"/database/column-stats", data
# 	)
# 	return column_stats
