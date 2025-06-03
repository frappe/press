# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import re
from collections import Counter

import frappe
import frappe.utils
from elasticsearch import Elasticsearch
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.site_activity.site_activity import log_site_activity


class SiteDatabaseUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site_database_table_permission.site_database_table_permission import (
			SiteDatabaseTablePermission,
		)

		failed_agent_job: DF.Link | None
		failure_reason: DF.SmallText
		label: DF.Data
		max_connections: DF.Int
		mode: DF.Literal["read_only", "read_write", "granular"]
		password: DF.Password
		permissions: DF.Table[SiteDatabaseTablePermission]
		site: DF.Link
		status: DF.Literal["Pending", "Active", "Failed", "Archived"]
		team: DF.Link
		user_added_in_proxysql: DF.Check
		user_created_in_database: DF.Check
		username: DF.Data
	# end: auto-generated types

	dashboard_fields = (
		"label",
		"status",
		"site",
		"username",
		"team",
		"mode",
		"failed_agent_job",
		"failure_reason",
		"permissions",
		"max_connections",
	)

	def validate(self):
		if not self.has_value_changed("status"):
			self._raise_error_if_archived()
		# remove permissions if not granular mode
		if self.mode != "granular":
			self.permissions.clear()

		if not self.is_new() and self.has_value_changed("max_connections"):
			frappe.throw("You can't update the max database connections. Archive it and create a new one.")

		if not self.max_connections:
			frappe.throw(
				"Max database connections can't be zero. You need to opt for at least one connection."
			)

	def before_insert(self):
		site = frappe.get_doc("Site", self.site)
		if not site.has_permission():
			frappe.throw("You don't have permission to create database user")
		if not frappe.db.get_value("Site Plan", site.plan, "database_access"):
			frappe.throw(f"Database Access is not available on {site.plan} plan")

		# validate connection limit
		exists_db_users_connection_limit = frappe.db.get_all(
			"Site Database User",
			{"site": self.site, "status": ("!=", "Archived")},
			pluck="max_connections",
		)
		total_used_connections = sum(exists_db_users_connection_limit)
		allowed_max_connections_for_site = site.database_access_connection_limit - total_used_connections
		if self.max_connections > allowed_max_connections_for_site:
			frappe.throw(
				f"Your site has quota of {site.database_access_connection_limit} database connections.\nYou can't allocate more than {allowed_max_connections_for_site} connections for new user. You can drop other database users to allocate more connections."
			)

		self.status = "Pending"
		if not self.username:
			self.username = frappe.generate_hash(length=15)
		if not self.password:
			self.password = frappe.generate_hash(length=20)

	def after_insert(self):
		log_site_activity(
			self.site,
			"Create Database User",
			reason=f"Created user {self.username} with {self.mode} permission",
		)
		if hasattr(self.flags, "ignore_after_insert_hooks") and self.flags.ignore_after_insert_hooks:
			"""
			Added for make it easy to migrate records of db access users from site doctype to site database user
			"""
			return
		self.apply_changes()

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Archived":
			log_site_activity(
				self.site,
				"Remove Database User",
				reason=f"Removed user {self.username} with {self.mode} permission",
			)

	def _raise_error_if_archived(self):
		if self.status == "Archived":
			frappe.throw("user has been deleted and no further changes can be made")

	def _get_database_name(self):
		site = frappe.get_doc("Site", self.site)
		db_name = site.fetch_info().get("config", {}).get("db_name")
		if not db_name:
			frappe.throw("Failed to fetch database name of site")
		return db_name

	@dashboard_whitelist()
	def save_and_apply_changes(self, label: str, mode: str, permissions: list):  # noqa: C901
		if self.status == "Pending" or self.status == "Archived":
			frappe.throw(f"You can't modify information in {self.status} state. Please try again later")

		self.label = label
		is_db_user_configuration_changed = self.mode != mode or self._is_permissions_changed(permissions)
		if is_db_user_configuration_changed:
			self.mode = mode
			new_permissions = permissions
			new_permission_tables = [p["table"] for p in new_permissions]
			current_permission_tables = [p.table for p in self.permissions]
			# add new permissions
			for permission in new_permissions:
				if permission["table"] not in current_permission_tables:
					self.append("permissions", permission)
			# modify permissions
			for permission in self.permissions:
				for new_permission in new_permissions:
					if permission.table == new_permission["table"]:
						permission.update(new_permission)
						break
			# delete permissions which are not in the modified list
			self.permissions = [p for p in self.permissions if p.table in new_permission_tables]

		self.save()
		if is_db_user_configuration_changed:
			self.apply_changes()

	def _is_permissions_changed(self, new_permissions):
		if len(new_permissions) != len(self.permissions):
			return True

		for permission in new_permissions:
			for p in self.permissions:
				if permission["table"] == p.table and (
					permission["mode"] != p.mode
					or permission["allow_all_columns"] != p.allow_all_columns
					or Counter(permission["selected_columns"]) != Counter(p.selected_columns)
				):
					return True

		return False

	@frappe.whitelist()
	def apply_changes(self):
		if not self.user_created_in_database:
			self.create_user()
		elif not self.user_added_in_proxysql:
			self.add_user_to_proxysql()
		else:
			self.modify_permissions()

		self.status = "Pending"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_user(self):
		self._raise_error_if_archived()
		agent = Agent(frappe.db.get_value("Site", self.site, "server"))
		agent.create_database_user(
			frappe.get_doc("Site", self.site), self.username, self.get_password("password"), self.name
		)

	@frappe.whitelist()
	def remove_user(self):
		self._raise_error_if_archived()
		agent = Agent(frappe.db.get_value("Site", self.site, "server"))
		agent.remove_database_user(
			frappe.get_doc("Site", self.site),
			self.username,
			self.name,
		)

	@frappe.whitelist()
	def add_user_to_proxysql(self):
		self._raise_error_if_archived()
		database = self._get_database_name()
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		database_server_name = frappe.db.get_value(
			"Bench", frappe.db.get_value("Site", self.site, "bench"), "database_server"
		)
		database_server = frappe.get_doc("Database Server", database_server_name)
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.add_proxysql_user(
			frappe.get_doc("Site", self.site),
			database,
			self.username,
			self.get_password("password"),
			self.max_connections,
			database_server,
			reference_doctype="Site Database User",
			reference_name=self.name,
		)

	@frappe.whitelist()
	def remove_user_from_proxysql(self):
		self._raise_error_if_archived()
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.remove_proxysql_user(
			frappe.get_doc("Site", self.site),
			self.username,
			reference_doctype="Site Database User",
			reference_name=self.name,
		)

	@frappe.whitelist()
	def modify_permissions(self):
		self._raise_error_if_archived()
		log_site_activity(
			self.site,
			"Modify Database User Permissions",
			reason=f"Modified user {self.username} with {self.mode} permission",
		)
		server = frappe.db.get_value("Site", self.site, "server")
		agent = Agent(server)
		table_permissions = {}

		if self.mode == "granular":
			for x in self.permissions:
				table_permissions[x.table] = {
					"mode": x.mode,
					"columns": "*"
					if x.allow_all_columns
					else [c.strip() for c in x.selected_columns.splitlines() if c.strip()],
				}

		agent.modify_database_user_permissions(
			frappe.get_doc("Site", self.site),
			self.username,
			self.mode,
			table_permissions,
			self.name,
		)

	@dashboard_whitelist()
	def get_credential(self):
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		database = self._get_database_name()
		return {
			"host": proxy_server,
			"port": 3306,
			"database": database,
			"username": self.username,
			"password": self.get_password("password"),
			"mode": self.mode,
			"max_connections": self.max_connections,
		}

	@dashboard_whitelist()
	def archive(self, raise_error: bool = True, skip_remove_db_user_step: bool = False):
		if not raise_error and self.status == "Archived":
			return
		self._raise_error_if_archived()
		self.status = "Pending"
		self.save()

		if self.user_created_in_database and not skip_remove_db_user_step:
			"""
			If we are dropping the database, there is no need to drop
			db users separately.
			In those cases, use `skip_remove_db_user_step` param to skip it
			"""
			self.remove_user()
		else:
			self.user_created_in_database = False
			self.save()

		if self.user_added_in_proxysql:
			self.remove_user_from_proxysql()

		if not self.user_created_in_database and not self.user_added_in_proxysql:
			self.status = "Archived"
			self.save()

	@dashboard_whitelist()
	def fetch_logs(
		self, start_timestamp: int, end_timestamp: int, search_string: str = "", client_ip: str = ""
	):
		if abs(start_timestamp - end_timestamp) > 2592000:
			frappe.throw(
				"You can only search through at max 30 days of logs. Please try again with a smaller range."
			)
		try:
			log_server = frappe.db.get_single_value("Press Settings", "log_server")

			if not log_server:
				return []

			query = {
				"bool": {
					"filter": [
						{"term": {"event.dataset": "proxysql.events"}},
						{"term": {"username": self.username}},
						{
							"range": {
								"@timestamp": {
									"gte": int(start_timestamp) * 1000,  # Convert to milliseconds
									"lte": int(end_timestamp) * 1000,  # Convert to milliseconds
								}
							}
						},
					],
					"must": [],
					"must_not": [],
					"should": [],
				}
			}

			if search_string and search_string.strip() != "*":
				query["bool"]["must"].append(
					{"wildcard": {"query": {"value": f"*{search_string}*", "case_insensitive": True}}}
				)

			if client_ip:
				query["bool"]["filter"].append({"term": {"client_ip": client_ip}})

			url = f"https://{log_server}/elasticsearch/"
			password = get_decrypted_password("Log Server", log_server, "kibana_password")
			client = Elasticsearch(url, basic_auth=("frappe", password))
			result = client.search(
				size=500,
				index="filebeat-*",
				query=query,
				_source=["query", "client_ip", "start_timestamp", "duration_ms"],
			)
			# Only return the _source part of each hit
			hits = [hit["_source"] for hit in result["hits"]["hits"]]
			for i in range(len(hits)):
				hits[i]["start_timestamp"] = int(
					frappe.utils.cint(hits[i].get("start_timestamp"), 0) / 1000
				)  # Convert to seconds
			return hits
		except Exception:
			frappe.throw("Failed to fetch logs from log server. Please try again later.")

	@staticmethod
	def process_job_update(job):  # noqa: C901
		if job.status not in ("Success", "Failure"):
			return

		if not job.reference_name or not frappe.db.exists("Site Database User", job.reference_name):
			return

		doc: SiteDatabaseUser = frappe.get_doc("Site Database User", job.reference_name)

		if job.status == "Failure":
			doc.status = "Failed"
			doc.failed_agent_job = job.name
			if job.job_type == "Modify Database User Permissions":
				doc.failure_reason = SiteDatabaseUser.user_addressable_error_from_stacktrace(job.traceback)
			doc.save(ignore_permissions=True)
			return

		if job.job_type == "Create Database User":
			doc.user_created_in_database = True
			if not doc.user_added_in_proxysql:
				doc.add_user_to_proxysql()
		if job.job_type == "Remove Database User":
			doc.user_created_in_database = False
		elif job.job_type == "Add User to ProxySQL":
			doc.user_added_in_proxysql = True
			doc.modify_permissions()
		elif job.job_type == "Remove User from ProxySQL":
			doc.user_added_in_proxysql = False
		elif job.job_type == "Modify Database User Permissions":
			doc.status = "Active"

		doc.save(ignore_permissions=True)
		doc.reload()

		if (
			job.job_type in ("Remove Database User", "Remove User from ProxySQL")
			and not doc.user_added_in_proxysql
			and not doc.user_created_in_database
		):
			doc.archive()

	@staticmethod
	def user_addressable_error_from_stacktrace(stacktrace: str):
		pattern = r"peewee\.\w+Error: (.*)?"
		default_error_msg = "Unknown error. Please try again.\nIf the error persists, please contact support."

		matches = re.findall(pattern, stacktrace)
		if len(matches) == 0:
			return default_error_msg
		data = matches[0].strip().replace("(", "").replace(")", "").split(",", 1)
		if len(data) != 2:
			return default_error_msg

		if data[0] == "1054":
			pattern = r"Unknown column '(.*)' in '(.*)'\"*?"
			matches = re.findall(pattern, data[1])
			if len(matches) == 1 and len(matches[0]) == 2:
				return f"Column '{matches[0][0]}' doesn't exist in '{matches[0][1]}' table.\nPlease remove the column from permissions configuration and apply changes."

		elif data[0] == "1146":
			pattern = r"Table '(.*)' doesn't exist"
			matches = re.findall(pattern, data[1])
			if len(matches) == 1 and isinstance(matches[0], str):
				table_name = matches[0]
				table_name = table_name.split(".")[-1]
				return f"Table '{table_name}' doesn't exist.\nPlease remove it from permissions table and apply changes."

		return default_error_msg


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site Database User")
