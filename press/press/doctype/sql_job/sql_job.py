# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

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
		row_limit: DF.Int
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
		"""
		Comment at the end of the query is important

		<type>_<query_id_or_type_info>

		query_a6gd59dsd -> In response, there will be record with query id is a6gd59dsd and type is query
		profile_a6gd59dsd -> In response, there will be record with query id is a6gd59dsd and type is profile
		"""
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

			# If it's a select query apply the limit
			if self.row_limit and q.is_select_query():
				query = f"SELECT * FROM ({query}) AS t LIMIT {self.row_limit}"

			# Add the query id to the query
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
				data = response.get("data")
				# process the response
				self.process_response("Success", data)
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

	def process_response(self, status: str, response: list[dict] | None = None):  # noqa: C901
		if status not in ["Success", "Failure"]:
			return
		if response is None:
			response = []

		self.status = status
		if self.status == "Success":
			"""
			Expected response format:
			[
				{
					"success": True,
					"id": query_id / type,
					"type": query_type [query / profile / config],
					"columns": [],
					"data": [],
					"row_count": row_count,
					"duration": duration (in seconds),
					"error_code": mysql error code (0 if unknown error),
					"error_message": mysql error message,
				}
			]
			"""
			# Store the self.queries in a map
			query_map = {q.name: q for q in self.queries}
			for row in response:
				record_type = row.get("type")
				if record_type not in ["query", "profile"]:
					# No need to process other types [i.e. config]
					continue

				query_id = row.get("id")
				if query_id not in query_map:
					continue

				if record_type == "query":
					query_map[query_id].success = row.get("success", False)
					query_map[query_id].duration = row.get("duration", 0)
					query_map[query_id].row_count = row.get("row_count", 0)
					query_map[query_id].error_code = row.get("error_code", 0)
					query_map[query_id].error_message = row.get("error_message", "")
					query_map[query_id].data = json.dumps(row.get("data", []))
					query_map[query_id].columns = json.dumps(row.get("columns", []))

				elif record_type == "profile":
					columns = row.get("columns", [])
					profile_data = row.get("data", [])
					query_map[query_id].profile = json.dumps(
						list(map(lambda x: dict(zip(columns, x)), profile_data))
					)

		self.save()
		process_sql_job_updates(self)

	def get_database_root_password(self):
		if self.target_type == "Database Server":
			return get_decrypted_password("Database Server", self.target_document, "mariadb_root_password")
		if self.target_type == "Site":
			return get_mariadb_root_password(frappe.get_doc("Site", self.target_document))
		raise frappe.ValidationError("Invalid target type")

	def get_database_host(self):
		if self.target_type == "Database Server":
			return frappe.get_cached_value("Database Server", self.target_document, "private_ip")
		if self.target_type == "Site":
			return get_mariadb_host(frappe.get_doc("Site", self.target_document))
		raise frappe.ValidationError("Invalid target type")

	def get_database_port(self):
		if self.target_type == "Database Server":
			return 3306
		if self.target_type == "Site":
			return get_mariadb_port(frappe.get_doc("Site", self.target_document))
		raise frappe.ValidationError("Invalid target type")

	def get_database_root_user(self):
		if self.target_type == "Database Server":
			return frappe.get_cached_value("Database Server", self.target_document, "mariadb_root_user")
		if self.target_type == "Site":
			return get_mariadb_root_user(frappe.get_doc("Site", self.target_document))
		raise frappe.ValidationError("Invalid target type")

	@staticmethod
	def run_queries(
		queries: str | list[str],
		target_type: Literal["Database Server", "Site"],
		target: str,
		mode: Literal["r", "rw"] = "r",
		user: Literal["Root User", "Site User"] = "Root User",
		type: str = "Generic",
		allow_ddl_query: bool = False,
		allow_any_query: bool = False,
		async_task: bool = False,
		continue_on_error: bool = False,
		wait_timeout: int = 30,
		lock_wait_timeout: int = 30,
		max_statement_time: int = 600,
		profiling: bool = False,
	) -> SQLJob:
		"""Execute SQL queries against a database target.

		Args:
			queries: Single multiline SQL query string or list of queries to execute
			target_type: Type of target - "Database Server" or "Site"
			target: Name of the target database server or site
			mode: Access mode - "r" for read-only, "rw" for read-write
			user: User type to execute as - "Root User" or "Site User"
			type: Job type label [Useful for callbacks]
			allow_ddl_query: Allow DDL (Data Definition Language) queries
			allow_any_query: Allow any type of query without restrictions
			async_task: Run queries asynchronously via agent job
			continue_on_error: Continue executing remaining queries if one fails
			wait_timeout: Session wait timeout in seconds
			lock_wait_timeout: Lock wait timeout in seconds
			max_statement_time: Maximum time limit for statement execution in seconds
			profiling: Enable query profiling

		Returns:
			SQLJob: Created SQL Job document
		"""

		if not queries:
			frappe.throw("No queries provided")

		if isinstance(queries, str):
			queries = queries.split(";")
			queries = [q.strip() for q in queries]
			queries = [q for q in queries if q]

		doc: SQLJob = frappe.get_doc(
			{
				"doctype": "SQL Job",
				"target_document": target,
				"target_type": target_type,
				"job_type": type,
				"async_task": async_task,
				"queries": [{"query": q} for q in queries],
				"wait_timeout": wait_timeout,
				"lock_wait_timeout": lock_wait_timeout,
				"max_statement_time": max_statement_time,
				"user_type": user,
				"read_only": mode != "rw",
				"profile_query": profiling,
				"continue_on_error": continue_on_error,
				"allow_ddl_query": allow_ddl_query,
				"allow_any_query": allow_any_query,
			}
		)
		doc.insert()
		doc.start()
		return doc

	@staticmethod
	def get_status(name: str) -> str:
		return frappe.db.get_value("SQL Job", name, "status")


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
	frappe.db.set_value("Agent Job", job.name, "data", "")


def process_sql_job_updates(job: SQLJob):
	pass
