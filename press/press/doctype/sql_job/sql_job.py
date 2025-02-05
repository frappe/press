# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
import sqlparse
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

from press.agent import Agent
from press.utils import get_mariadb_host, get_mariadb_port, get_mariadb_root_password, get_mariadb_root_user

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.site.site import Site


class SQLJob(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.sql_job_query.sql_job_query import SQLJobQuery

		allow_any_query: DF.Check
		allow_ddl_query: DF.Check
		async_task: DF.Check
		continue_on_error: DF.Check
		database_name: DF.Data | None
		job: DF.Link | None
		job_type: DF.Data
		lock_wait_timeout: DF.Int
		max_statement_time: DF.Int
		prepared_sql_statement: DF.LongText | None
		profile_query: DF.Check
		queries: DF.Table[SQLJobQuery]
		read_only: DF.Check
		server: DF.Link | None
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
		if self.target_type == "Database Server" and self.user_type != "Root User":
			frappe.throw("Only root user can run queries on database servers")

	def before_insert(self):
		self.set_app_server()
		self.set_database_name()
		self.format_queries()
		self.skip_invalid_queries()

	def set_app_server(self):
		if self.target_type == "Site":
			self.server = frappe.db.get_value("Site", self.target_document, "server")
		elif self.target_type == "Database Server":
			database_server = self.target_document

			# Try to find primary database server in case of replica setup
			is_primary_db = frappe.db.get_value("Database Server", database_server, "is_primary")
			if not is_primary_db:
				database_server = frappe.db.get_value("Database Server", database_server, "primary")

			self.server = frappe.db.get_value(
				"Server",
				{
					"database_server": database_server,
					"status": ["!=", "Archived"],
				},
			)

	def set_database_name(self):
		if self.target_type == "Database Server":
			if not self.database_name:
				# Default to mysql table
				self.database_name = "mysql"
		elif self.target_type == "Site":
			self.database_name = frappe.db.get_value("Site", self.target_document, "database_name")
			if not self.database_name:
				site: Site = frappe.get_doc("Site", self.target_document)
				site.sync_info()
				self.database_name = site.database_name
		else:
			raise frappe.ValidationError("Invalid target type")

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
			f"SET SESSION wait_timeout = {self.wait_timeout} /* config_wait_timeout */;",
			f"SET SESSION lock_wait_timeout = {self.lock_wait_timeout} /* config_lock_wait_timeout */;",
			f"SET SESSION max_statement_time = {self.max_statement_time} /* config_statement_time */;",
		]
		if self.profile_query:
			statements.append("SET SESSION profiling = 1 /* config_profiling */;")

		# Add the queries
		for q in self.queries:
			if q.skip:
				continue
			# Insert variables
			query = q.query.replace("{{database_name}}", self.database_name)
			statements.append(f"{query} /* query_{q.name} */;")

		# Add profiling statements
		if self.profile_query:
			for i, q in enumerate(self.queries):
				if q.skip:
					continue
				statements.append(f"SHOW PROFILE ALL FOR QUERY {i + 1} /* profile_{q.name} */;")
		return statements

	@frappe.whitelist()
	def start(self):
		self.status = "Running"
		agent = Agent(self.server)
		try:
			response = agent.run_sql(self)
			if self.async_task:
				self.job = response
			else:
				# process the response
				self.process_response("Success", response)
		except Exception:
			self.status = "Failure"
		finally:
			self.save()

	@frappe.whitelist()
	def cancel(self):
		if not self.job:
			return
		job: AgentJob = frappe.get_doc("Agent Job", self.job)
		job.cancel_job()

	def process_response(self, status: str, response: list[dict] | None = None):
		if status not in ["Success", "Failure"]:
			return
		self.status = status
		if self.status == "Success":
			# update queries
			return
		self.save()
		process_sql_job_updates(self)

	def get_database_root_password(self):
		if self.target_type == "Database Server":
			return get_decrypted_password("Database Server", self.target_document, "mariadb_root_password")
		if self.target_type == "Site":
			return get_mariadb_root_password(self.target_document)
		raise frappe.ValidationError("Invalid target type")

	def get_database_host(self):
		if self.target_type == "Database Server":
			return frappe.get_cached_value("Database Server", self.target_document, "private_ip")
		if self.target_type == "Site":
			return get_mariadb_host(self.target_document)
		raise frappe.ValidationError("Invalid target type")

	def get_database_port(self):
		if self.target_type == "Database Server":
			return 3306
		if self.target_type == "Site":
			return get_mariadb_port(self.target_document)
		raise frappe.ValidationError("Invalid target type")

	def get_database_root_user(self):
		if self.target_type == "Database Server":
			return frappe.get_cached_value("Database Server", self.target_document, "mariadb_root_user")
		if self.target_type == "Site":
			return get_mariadb_root_user(self.target_document)
		raise frappe.ValidationError("Invalid target type")


def process_agent_job_update(job: AgentJob):
	if job.status not in ["Success", "Failure", "Delivery Failure"]:
		return
	sql_job: SQLJob = frappe.get_doc("SQL Job", job.reference_name)
	job_data = None
	try:
		job_data = json.loads(job.data)
	except Exception:
		job_data = None
	sql_job.process_response(job.status, job_data)


def process_sql_job_updates(job: SQLJob):
	pass
