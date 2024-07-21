import json
from typing import TYPE_CHECKING

import frappe
from press.agent import Agent
from press.api.site import protected

from press.press.report.mariadb_slow_queries.mariadb_slow_queries import (
	OptimizeDatabaseQuery,
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
		}
	)
	for table_name in tables:
		doc.append("tables_in_query", {"table": table_name})
	doc.save()
	# if index := analyzer.analyze():
	#     row["suggested_index"] = f"{index.table}.{index.column}"
	return tables


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
