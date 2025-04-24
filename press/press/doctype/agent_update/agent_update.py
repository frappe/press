# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import datetime

import frappe
import requests
from frappe.model.document import Document

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
		rollback_to_specific_commit: DF.Check
		servers: DF.Table[AgentUpdateServer]
		start: DF.Datetime | None
		status: DF.Literal["Draft", "Planning", "Pending", "Running", "Rollbacking", "Success", "Failure"]
		stuck_at_planning_reason: DF.SmallText | None
	# end: auto-generated types

	def validate(self):
		pass

	@property
	def repo_name(self):
		return self.repo.split("/")[-1]

	@property
	def repo_owner(self):
		return self.repo.split("/")[-2]

	def before_insert(self):  # noqa: C901
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

		# Verify rollback commit hash
		if self.auto_rollback_changes and self.rollback_to_specific_commit:
			if not self.default_rollback_commit:
				frappe.throw("Rollback commit hash is required when rollback to specific commit is enabled")

			if self.fetch_commit_date(self.default_rollback_commit) is None:
				frappe.throw("Rollback commit hash is not valid")

		# Add servers
		self.add_server_entries()

	def add_server_entries(self):
		filters = {"status": "Active"}
		if self.exclude_self_hosted_servers:
			filters.update({"is_self_hosted": 0})

		if self.app_server:
			servers = frappe.get_all("Server", filters, pluck="name")
			for server in servers:
				self.append("servers", {"server": server, "server_type": "Server", "status": "Draft"})

		if self.database_server:
			servers = frappe.get_all("Database Server", filters, pluck="name")
			for server in servers:
				self.append(
					"servers", {"server": server, "server_type": "Database Server", "status": "Draft"}
				)
		if self.proxy_server:
			servers = frappe.get_all("Proxy Server", filters, pluck="name")
			for server in servers:
				self.append("servers", {"server": server, "server_type": "Proxy Server", "status": "Draft"})

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

	def _create_execution_plan(self):  # noqa: C901
		self.status = "Planning"
		self.save()
		frappe.db.commit()

		self.stuck_at_planning_reason = ""

		# Fetch commit hash of each agent
		# Set to unknown if not found
		self.stuck_at_planning_reason += (
			"Fetching commit hash from server. If it fails, resolve the issue and then resume again\n"
		)
		for s in self.servers:
			if s.status == "Pending":
				continue

			with contextlib.suppress(Exception):
				agent = Agent(s.server, server_type=s.server_type)
				commit = agent.get_version()["commit"]
				s.current_commit = commit
				s.status = "Pending"

				if self.auto_rollback_changes:
					if self.rollback_to_specific_commit:
						s.rollback_commit = self.default_rollback_commit
					else:
						s.rollback_commit = commit

			if not s.current_commit:
				self.stuck_at_planning_reason += f"- {s.server}\n"

		# Decide whether rollback possible, we can't auto rollback for very old agents
		# Because agent doesn't has the rollback facility before 22nd April 2025
		self.stuck_at_planning_reason += "\nChecking if agent rollback impossible due to old commit hash. If found any, please update the agent manually\n"
		for s in self.servers:
			if s.status != "Pending":
				continue

			if not self.is_commit_supported(s.current_commit):
				self.stuck_at_planning_reason += f"- {s.server} - {s.current_commit}\n"
				s.status = "Draft"  # Move status to Draft

		# Mark same commit hash servers as Skipped
		for s in self.servers:
			if s.current_commit == self.commit_hash:
				s.status = "Skipped"

		# Change status from `Planning` to `Pending` if all sites are `Pending`
		is_all_server_ready = all(s.status in ("Pending", "Skipped") for s in self.servers)
		if is_all_server_ready:
			self.status = "Pending"

		if not is_all_server_ready:
			self.stuck_at_planning_reason += "\nPlease fix the server's issue or remove it from the list."

		self.save()

	def fetch_commit_hash(self, ref: str) -> str:
		res = requests.get(f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{ref}")
		res.raise_for_status()
		return res.json().get("sha")

	def fetch_commit_date(self, ref: str) -> datetime.datetime | None:
		res = requests.get(f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{ref}")
		res.raise_for_status()
		return datetime.datetime.strptime(
			res.json().get("commit").get("committer").get("date"), "%Y-%m-%dT%H:%M:%SZ"
		)

	def is_commit_supported(self, ref: str) -> bool:
		date_limit = datetime.datetime(2025, 4, 22)
		commit_date = self.fetch_commit_date(ref)
		if commit_date is None:
			return True
		if commit_date > date_limit:
			return False
		return True
