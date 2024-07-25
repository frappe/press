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
	if mariadb_analyze_query_already_exists(site, row["example"]):
		return "Failure"
	doc = frappe.get_doc(
		{
			"doctype": "MariaDB Analyze Query",
			"site": site,
			"tables_in_query": [],
		}
	)
	doc.status = "Running"

	query = row["example"]
	doc.query = query
	if not query.lower().startswith(("select", "update", "delete")):
		doc.status = "Failure"
		doc.save()
		frappe.db.commit()
		return

	doc.save()
	frappe.db.commit()

	analyzer = OptimizeDatabaseQuery(site, query)
	explain_output = analyzer.fetch_explain() or []
	explain_output = [DBExplain.from_frappe_ouput(e) for e in explain_output]
	doc.explain_output = json.dumps(explain_output)

	optimizer = DBOptimizer(query=analyzer.query, explain_plan=explain_output)
	for table in optimizer.tables_examined:
		stats = _fetch_table_stats(analyzer.site, table)
		doc.append("tables_in_query", {"table": table, "table_statistics": json.dumps(stats)})

		if not stats:
			# Old framework version
			doc.status = "Failure"
			doc.save()
			frappe.db.commit()
			return

		# This is an agent job. Remaining is processed in the callback.
		_fetch_column_stats(analyzer.site, table, doc.get_title())

	doc.save()
	return doc.status


def check_if_all_fetch_column_stats_was_sucessful(doc):
	for item in doc.tables_in_query:
		if not item.status == "Success":
			return False
	return True


def fetch_column_stats_update(job, response_data):
	doc_name = response_data["data"]["doc_name"]
	table = json.loads(job.request_data)["table"]

	if job.status == "Success":
		column_statistics = response_data["steps"][0]["data"]["output"]
		doc = frappe.get_doc("MariaDB Analyze Query", doc_name)
		for item in doc.tables_in_query:
			if item.table == table:
				item.column_statistics = column_statistics
				item.status = "Success"
				doc.save()
				frappe.db.commit()
		if check_if_all_fetch_column_stats_was_sucessful(doc):
			doc.status = "Success"
			doc.save()
			frappe.db.commit()
			# Perisists within doctype
			get_suggested_index(doc)
	elif job.status == "Failure":
		doc = frappe.get_doc("MariaDB Analyze Query", doc_name)
		for item in doc.tables_in_query:
			if item.table == table:
				item.status = "Failure"
				doc.save()

		doc.status = "Failure"
		doc.save()
		frappe.db.commit()


def get_suggested_index(doc):
	explain_output = json.loads(doc.explain_output)
	optimizer = DBOptimizer(query=doc.query, explain_plan=explain_output)
	for item in doc.tables_in_query:
		stats = json.loads(item.table_statistics)
		if not stats:
			# Old framework version
			return
		db_table = DBTable.from_frappe_ouput(stats)
		column_stats = json.loads(item.column_statistics)
		column_stats = [ColumnStat.from_frappe_ouput(c) for c in column_stats]
		db_table.update_cardinality(column_stats)
		optimizer.update_table_data(db_table)
	index = optimizer.suggest_index()
	doc.suggested_index = f"{index.table}.{index.column}"
	doc.save()


@frappe.whitelist()
@protected("Site")
def get_status_of_mariadb_analyze_query(name, query):
	filters = {"site": name, "query": query}
	doc = frappe.get_all(
		"MariaDB Analyze Query",
		filters=filters,
		fields=["status", "suggested_index"],
		limit=1,
	)
	if doc:
		return doc[0]
	else:
		return None


def mariadb_analyze_query_already_exists(site, query):
	if frappe.db.exists("MariaDB Analyze Query", {"site": site, "query": query}):
		return True
	return False
