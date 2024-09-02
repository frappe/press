import json

import frappe
from press.utils import log_error

from press.api.site import protected

from press.press.report.mariadb_slow_queries.mariadb_slow_queries import (
	OptimizeDatabaseQuery,
	_fetch_column_stats,
	_fetch_table_stats,
)
from press.press.report.mariadb_slow_queries.db_optimizer import (
	ColumnStat,
	DBExplain,
	DBOptimizer,
	DBTable,
)


@frappe.whitelist()
@protected("Site")
def mariadb_analyze_query(name, row):
	suggested_index = analyze_query(row=row, site=name)
	return suggested_index


def analyze_query(row, site):
	# if mariadb_analyze_query_already_exists(site, row["query"]):
	#     frappe.throw("The query seems to have already been optimized")
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
	doc.normalized_query = row["query"]

	if not query.lower().startswith(("select", "update", "delete")):
		doc.status = "Failure"
		doc.save()
		frappe.db.commit()
		return

	doc.save()
	frappe.db.commit()

	analyzer = OptimizeDatabaseQuery(site, query)
	explain_output = analyzer.fetch_explain() or []
	doc.explain_output = json.dumps(explain_output)
	explain_output = [DBExplain.from_frappe_ouput(e) for e in explain_output]

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
			save_suggested_index(doc)
	elif job.status == "Failure":
		doc = frappe.get_doc("MariaDB Analyze Query", doc_name)
		for item in doc.tables_in_query:
			if item.table == table:
				item.status = "Failure"
				doc.save()

		doc.status = "Failure"
		doc.save()
		frappe.db.commit()


def save_suggested_index(doc):
	explain_output = json.loads(doc.explain_output)
	explain_output = [DBExplain.from_frappe_ouput(e) for e in explain_output]
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


def mariadb_analyze_query_already_exists(site, normalized_query):
	if frappe.db.exists(
		"MariaDB Analyze Query", {"site": site, "normalized_query": normalized_query}
	):
		return True
	return False


@frappe.whitelist()
@protected("Site")
def mariadb_analyze_query_already_running_for_site(name):
	if frappe.db.exists("MariaDB Analyze Query", {"site": name, "status": "Running"}):
		return True
	return False


@frappe.whitelist()
@protected("Site")
def get_suggested_index(name, normalized_query):
	suggested_index = frappe.get_value(
		"MariaDB Analyze Query",
		{"site": name, "status": "Success", "normalized_query": normalized_query},
		["site", "normalized_query", "suggested_index"],
		as_dict=True,
	)
	return suggested_index


def delete_all_occurences_of_mariadb_analyze_query(job):
	try:
		if job.status == "Success" or job.status == "Failure":
			frappe.db.delete("MariaDB Analyze Query", {"site": job.site})
			frappe.db.commit()
	except Exception as e:
		log_error("Deleting all occurences of MariaDB Analyze Query Failed", data=e)
