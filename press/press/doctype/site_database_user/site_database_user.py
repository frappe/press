# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
import re

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype


class SiteDatabaseUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site_database_table_permission.site_database_table_permission import (
			SiteDatabaseTablePermission,
		)

		database: DF.Data
		failed_agent_job: DF.Link | None
		failure_reason: DF.SmallText
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
		"status",
		"site",
		"team",
		"user_added_in_proxysql",
		"user_created_in_database",
		"username",
		"mode",
		"failed_agent_job",
		"failure_reason",
		"permissions",
	)

	def validate(self):
		if not self.has_value_changed("status"):
			self._raise_error_if_archived()

	def before_insert(self):
		site = frappe.get_doc("Site", self.site)
		if not site.has_permission():
			frappe.throw("You don't have permission to create database user")
		self.status = "Pending"
		self.database = ""
		self.username = "user_" + frappe.generate_hash(length=10)
		self.password = frappe.generate_hash(length=15)

	def after_insert(self):
		self.apply_changes()

	def _raise_error_if_archived(self):
		if self.status == "Archived":
			frappe.throw("user has been deleted and no further changes can be made")

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
		if not self.database:
			# It's needed because press doesn't store the database name the site is using
			# so, at the time of creating database user, the database name will be stored
			# which can be utilized for adding user in proxysql
			frappe.throw("create the user in database first before adding to proxysql")
		server = frappe.db.get_value("Site", self.site, "server")
		proxy_server = frappe.db.get_value("Server", server, "proxy_server")
		database_server_name = frappe.db.get_value(
			"Bench", frappe.db.get_value("Site", self.site, "bench"), "database_server"
		)
		database_server = frappe.get_doc("Database Server", database_server_name)
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.add_proxysql_user(
			frappe.get_doc("Site", self.site),
			self.database,
			self.username,
			self.get_password("password"),
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
		return {
			"host": proxy_server,
			"port": 3306,
			"database": self.database,
			"username": self.username,
			"password": self.get_password("password"),
			"mode": self.mode,
		}

	@frappe.whitelist()
	def archive(self):
		self._raise_error_if_archived()
		if self.user_created_in_database:
			self.remove_user()
		if self.user_added_in_proxysql:
			self.remove_user_from_proxysql()

		if not self.user_created_in_database and not self.user_added_in_proxysql:
			self.status = "Archived"
			self.save(ignore_permissions=True)

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
			doc.database = json.loads(job.data).get("database")
			if not doc.database:
				frappe.throw("database name not found in the job response data")
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
