# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations
import contextlib
import datetime

import frappe
from frappe.model.document import Document
import requests

from press.agent import Agent


class AgentUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.agent_update_server.agent_update_server import AgentUpdateServer

		app_server: DF.Check
		auto_rollback_changes: DF.Check
		branch: DF.Data | None
		commit_hash: DF.Data | None
		database_server: DF.Check
		default_rollback_commit: DF.Data | None
		end: DF.Datetime | None
		exclude_self_hosted_servers: DF.Check
		proxy_server: DF.Check
		repo: DF.Data | None
		restart_background_workers: DF.Check
		restart_redis: DF.Check
		restart_web_workers: DF.Check
		servers: DF.Table[AgentUpdateServer]
		start: DF.Datetime | None
		status: DF.Literal["Draft", "Planning", "Running", "Rollbacking", "Success", "Failure"]
	# end: auto-generated types

	def validate(self):
		pass

	@property
	def repo_name(self):
		return self.repo.split("/")[-1]

	@property
	def repo_owner(self):
		return self.repo.split("/")[-2]

	def before_insert(self):
		self.status = "Draft"

		if not (self.app_server or self.database_server or self.proxy_server):
			frappe.throw("Please select at least one server type")

		# Set repo
		press_settings = frappe.get_single("Press Settings")
		if not self.repo:
			repository_owner = press_settings.agent_repository_owner or "frappe"
			self.repo = f"github.com/{repository_owner}/agent"
		if not self.branch:
			self.branch = press_settings.branch or "master"

		# Set commit hash
		if not self.commit_hash:
			self.commit_hash = self.fetch_commit_hash(self.branch)
		else:
			if self.fetch_commit_hash(self.branch) != self.commit_hash:
				frappe.throw("Commit hash looks in valid. Please recheck")

		# Add servers
		self.add_server_entries()

	def add_server_entries(self):
		filters = {"status": "Active"}
		if self.exclude_self_hosted_servers:
			filters.update({"is_self_hosted": 0})

		if self.app_server:
			servers = frappe.get_all("Server", filters, pluck="name")
			for server in servers:
				self.append("servers", {"server": server, "server_type": "Server", "status": "Pending"})

		if self.database_server:
			servers = frappe.get_all("Database Server", filters, pluck="name")
			for server in servers:
				self.append(
					"servers", {"server": server, "server_type": "Database Server", "status": "Pending"}
				)
		if self.proxy_server:
			servers = frappe.get_all("Proxy Server", filters, pluck="name")
			for server in servers:
				self.append("servers", {"server": server, "server_type": "Proxy Server", "status": "Pending"})

	@frappe.whitelist()
	def create_execution_plan(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_create_execution_plan",
			queue="long",
			timeout=1200,
			job_id=f"create_execution_plan:{self.name}",
			deduplicate=True,
			at_front=True,
		)

	def _create_execution_plan(self):
		self.status = "Planning"
		self.save()
		frappe.db.commit()
		# Fetch commit hash of each agent
		# Set to unknown if not found
		for s in self.servers:
			if s.current_commit and s.current_commit != "Unknown":
				continue

			with contextlib.suppress(Exception):
				agent = Agent(s.server, server_type=s.server_type)
				commit = agent.get_version()["commit"]
				s.current_commit = commit

			if not s.current_commit:
				s.current_commit = "Unknown"

		# Decide whether rollback possible, we can't auto rollback for very old agents
		for s in self.servers:
			if s.current_commit == "Unknown":
				s.is_rollback_possible = False
			else:
				# Rollback commit should be created after 22nd April 2025
				# Because agent doesn't has the rollback facility else
				date_limit = datetime.datetime(2025, 4, 22)
				commit_date = self.fetch_commit_date(s.current_commit)
				if commit_date and commit_date < date_limit:
					s.is_rollback_possible = True

		s.save()

	def fetch_commit_hash(self, ref: str) -> str:
		res = requests.get(f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{ref}")
		res.raise_for_status()
		return res.json().get("sha")

	def fetch_commit_date(self, ref: str) -> datetime.datetime | None:
		res = requests.get(f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{ref}")
		res.raise_for_status()
		return datetime.datetime.fromisoformat(res.json().get("commit").get("committer").get("date"))
