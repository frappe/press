# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
import json

import frappe
from frappe.model.document import Document
from press.agent import Agent
from press.api.site import protected

from press.press.doctype.optimize_database_query.db_optimizer import (
	ColumnStat,
	DBOptimizer,
	DBTable,
)


class OptimizeDatabaseQuery(Document):
	def validate(self):
		from press.press.report.mariadb_slow_queries.mariadb_slow_queries import format_query

		self.query = format_query(self.query)

	def analyze(self):
		self.db_set("status", "Started", commit=True)
		explain_output = self.fetch_explain()
		self.db_set("explain", json.dumps(explain_output))

		optimizer = DBOptimizer(query=self.query)
		tables = optimizer.tables_examined

		for table in tables:
			stats = self.fetch_table_stats(table)
			db_table = DBTable.from_frappe_ouput(stats)
			column_stats = self.fetch_column_stats(table)
			db_table.update_cardinality(column_stats)
			optimizer.update_table_data(db_table)

		if index := optimizer.suggest_index():
			self.db_set("suggested_index", f"{index.table}.{index.column}")
		frappe.msgprint("Query analysis successful", alert=True)
		self.db_set("status", "Completed", commit=True)

	def after_insert(self):
		frappe.msgprint("Queued query for analysis", alert=True)
		frappe.enqueue(self.analyze, enqueue_after_commit=True)

	@staticmethod
	def get_doctype_name(table_name: str) -> str:
		return table_name.removeprefix("tab")

	def fetch_explain(self) -> dict[str, str]:
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

	def fetch_table_stats(self, table: str):
		site = frappe.get_cached_doc("Site", self.site)
		agent = Agent(site.server)
		return agent.describe_database_table(
			site,
			doctype=self.get_doctype_name(table),
			columns=[],
		)

	def fetch_column_stats(self, table: str) -> list[ColumnStat]:
		site = frappe.get_cached_doc("Site", self.site)
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

	def add_suggested_index(self):
		if not self.suggested_index:
			frappe.throw("No index suggested")

		table, column = self.suggested_index.split(".")
		doctype = self.get_doctype_name(table)

		site = frappe.get_cached_doc("Site", self.site)
		agent = Agent(site.server)
		agent.add_database_index(site, doctype=doctype, columns=[column])

		# Update explain output
		explain_output = self.fetch_explain()
		self.db_set("explain", json.dumps(explain_output))


@frappe.whitelist()
@protected("Site")
def add_suggested_index(name: str, optimizer: str):
	optimizer = frappe.get_doc("Optimize Database Query", optimizer)
	if optimizer.site == name:
		frappe.enqueue(optimizer.add_suggested_index)
