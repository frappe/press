# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from collections import defaultdict
import frappe
from frappe.model.document import Document
from press.agent import Agent

from press.press.doctype.optimize_database_query.db_optimizer import (
	DBOptimizer,
	DBTable,
)


class OptimizeDatabaseQuery(Document):
	def validate(self):
		from press.press.report.mariadb_slow_queries.mariadb_slow_queries import format_query

		self.query = format_query(self.query)

	def analyze(self):
		self.db_set("status", "Started", commit=True)
		optimizer = DBOptimizer(query=self.query)
		tables = optimizer.tables_examined

		for table in tables:
			stats = self.fetch_table_stats(table)
			optimizer.update_table_data(DBTable.from_frappe_ouput(stats))

		# Fetch table info again because now we know potential columns
		indexes_to_evaluate = optimizer.potential_indexes()
		table_columns = defaultdict(set)
		for idx in indexes_to_evaluate:
			table_columns[idx.table].add(idx.column)

		for table, columns in table_columns.items():
			stats = self.fetch_table_stats(table, columns)
			optimizer.update_table_data(DBTable.from_frappe_ouput(stats))

		index = optimizer.suggest_index()
		self.db_set("suggested_index", str(index))
		frappe.msgprint("Query analysis successful", alert=True)
		self.db_set("status", "Completed", commit=True)

	def after_insert(self):
		frappe.msgprint("Queued query for analysis", alert=True)
		frappe.enqueue(self.analyze, enqueue_after_commit=True)

	@staticmethod
	def get_doctype_name(table_name: str) -> str:
		table_name.removeprefix("tab")

	def fetch_table_stats(self, table: str, columns: list[str] | None = None):
		if not columns:
			columns = []
		site = frappe.get_cached_doc("Site", self.site)
		agent = Agent(site.server)
		return agent.describe_database_table(
			site,
			doctype=self.get_doctype_name(table),
			columns=columns,
		)
