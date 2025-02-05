# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
import sqlparse
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


class SQLJob(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.sql_job_query.sql_job_query import SQLJobQuery

		allow_any_query: DF.Check
		allow_ddl_query: DF.Check
		continue_on_error: DF.Check
		database_name: DF.Data
		job: DF.Link | None
		job_type: DF.Data
		lock_wait_timeout: DF.Int
		max_statement_time: DF.Int
		prepared_sql_statement: DF.LongText | None
		profile_query: DF.Check
		queries: DF.Table[SQLJobQuery]
		read_only: DF.Check
		server: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		target_document: DF.DynamicLink
		target_type: DF.Literal["Site", "Database Server"]
		user_type: DF.Literal["Root User", "Site User"]
		wait_timeout: DF.Int
	# end: auto-generated types

	@property
	def prepared_sql_statement(self):
		return "\n".join(self.prepared_sql_statement_list)

	def validate(self):
		if self.read_only and (self.allow_any_query or self.allow_ddl_query):
			frappe.throw("You can run only DQL queries in read-only mode")

	def before_insert(self):
		self.format_queries()
		self.skip_invalid_queries()

	def format_queries(self):
		# Format queries
		for q in self.queries:
			q.query = sqlparse.format(q.query, reindent=False, strip_comments=True, strip_whitespace=True)
			if q.query.endswith(";"):
				q.query = q.query[:-1]

	def skip_invalid_queries(self):
		for query in self.queries:
			if not query.query:
				query.error_code = "EMPTY_QUERY"
				query.error_message = "Query is empty"
				query.skip = True
			elif not self.allow_ddl_query and query.is_ddl_query():
				query.error_code = "DDL_NOT_ALLOWED"
				query.error_message = "DDL queries are not allowed"
				query.skip = True
			elif not self.allow_any_query and query.is_restricted_query():
				query.error_code = "QUERY_RESTRICTED"
				query.error_message = "Query is restricted"
				query.skip = True

	@property
	def prepared_sql_statement_list(self) -> list[str]:
		statements = [
			f"SET SESSION wait_timeout = {self.wait_timeout} /* config_wait_timeout_ */;",
			f"SET SESSION lock_wait_timeout = {self.lock_wait_timeout} /* config_lock_wait_timeout */;",
			f"SET SESSION max_statement_time = {self.max_statement_time} /* config_statement_time */;",
		]
		if self.profile_query:
			statements.append("SET SESSION profiling = 1 /* config_profiling */;")

		# Add the queries
		for q in self.queries:
			if q.skip:
				continue
			statements.append(f"{q.query} /* query_{q.name} */;")

		# Add profiling statements
		if self.profile_query:
			for i, q in enumerate(self.queries):
				if q.skip:
					continue
				statements.append(f"SHOW PROFILE ALL FOR QUERY {i + 1} /* profile_{q.name} */;")
		return statements

	@frappe.whitelist()
	def start(self):
		pass

	@frappe.whitelist()
	def cancel(self):
		pass


def process_job_updates(job: AgentJob):
	pass
