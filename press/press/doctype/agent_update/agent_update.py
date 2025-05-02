# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import datetime

import frappe
import frappe.utils
import requests
from frappe.model.document import Document

from press.agent import Agent
from press.runner import Ansible


def bool_to_str(b: bool) -> str:
	return "true" if b else "false"


class AgentUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.agent_update_server.agent_update_server import AgentUpdateServer

		agent_startup_timeout_minutes: DF.Int
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
		restart_redis: DF.Check
		restart_rq_workers: DF.Check
		restart_web_workers: DF.Check
		rollback_to_specific_commit: DF.Check
		servers: DF.Table[AgentUpdateServer]
		start: DF.Datetime | None
		status: DF.Literal[
			"Draft", "Planning", "Pending", "Running", "Partial Success", "Success", "Paused", "Failure"
		]
		stop_after_rollback: DF.Check
		stuck_at_planning_reason: DF.SmallText | None
	# end: auto-generated types

	@property
	def repo_name(self):
		return self.repo.split("/")[-1]

	@property
	def repo_owner(self):
		return self.repo.split("/")[-2]

	@property
	def current_agent_update_to_process(self) -> AgentUpdateServer | None:
		if len(self.servers) == 0:
			return None

		for s in self.servers:
			if s.status in ("Pending", "Running", "Failure", "Rolling Back") or (
				s.status in ["Success", "Rolled Back"] and s.agent_status != "Active"
			):
				return s

		return None

	@property
	def last_terminated_agent_update(self) -> AgentUpdateServer | None:
		if len(self.servers) == 0:
			return None

		# check in reverse order
		for s in reversed(self.servers):
			if s.status in ["Success", "Rolled Back"] and s.agent_status == "Active":
				return s
			if s.status == "Fatal":
				return s

		return None

	@property
	def is_any_update_pending(self):
		return any(s.status == "Pending" for s in self.servers)

	@property
	def agent_update_args(self) -> str:
		return ""
		return f" --restart-web-workers={bool_to_str(self.restart_web_workers)} --restart-rq-workers={bool_to_str(self.restart_rq_workers)} --restart-redis={bool_to_str(self.restart_redis)} --skip-repo-setup --skip-patches"

	@property
	def agent_repository_url(self) -> str:
		return f"https://github.com/{self.repo_owner}/{self.repo_name}"

	def before_insert(self):  # noqa: C901
		self.status = "Draft"

		if not (self.app_server or self.database_server or self.proxy_server):
			frappe.throw("Please select at least one server type")

		if not self.agent_startup_timeout_minutes:
			self.agent_startup_timeout_minutes = 10

		# Set repo
		press_settings = frappe.get_single("Press Settings")
		if not self.repo:
			repository_owner = press_settings.agent_repository_owner or "frappe"
			self.repo = f"github.com/{repository_owner}/agent"
		if not self.branch:
			self.branch = press_settings.branch or "master"

		if self.repo.startswith("http://") or self.repo.startswith("https://"):
			frappe.throw("Please don't append http/https to the repo url")

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

	def on_update(self):
		if self.has_value_changed("status"):
			if self.status == "Running" and not self.start:
				self.start = frappe.utils.now_datetime()
			if self.status in ["Success", "Partial Success", "Failure"] and not self.end:
				self.end = frappe.utils.now_datetime()

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
		frappe.msgprint("Execution plan queued in background.")

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

	@frappe.whitelist()
	def pause(self):
		self.status = "Paused"
		self.save(ignore_version=True)

	@frappe.whitelist()
	def execute(self):
		if self.current_agent_update_to_process is None:
			return

		if self._process_next_step():
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"_update_agent_on_server",
				queue="long",
				timeout=2400,
				enqueue_after_commit=True,
				job_id=f"update_agent_on_server||{self.name}",
				deduplicate=True,
			)

	def _process_next_step(self) -> bool:  # noqa: C901
		"""
		Return True: if we need to trigger agent update on server
		"""
		# Update Status to Running
		if self.status != "Running":
			self.start = frappe.utils.now_datetime()
			self.status = "Running"
			self.save()

		if self.current_agent_update_to_process is None:
			return False

		current_agent_update_to_process = self.current_agent_update_to_process
		last_terminated_agent_update = self.last_terminated_agent_update

		# Decide status on termination
		if self.is_any_update_pending or (
			last_terminated_agent_update
			and (
				last_terminated_agent_update.status == "Fatal"
				or (
					last_terminated_agent_update.status == "Rolled Back"
					and last_terminated_agent_update.agent_status == "Active"
					and self.stop_after_rollback
				)
			)
		):
			# Status can be - Success, Failure, Partial Success

			no_of_successful_updates = sum(1 for server in self.servers if server.status == "Success")

			# Fatal / Rolled Back both are considered as failed
			no_of_failed_updates = sum(
				1 for server in self.servers if server.status == "Fatal" or server.status == "Rolled Back"
			)

			if no_of_successful_updates > 0:
				self.status = "Success"

			if no_of_failed_updates > 0:
				self.status = "Partial Success" if self.status == "Success" else "Failure"

			if self.status not in ["Success", "Partial Success", "Failure"]:
				self.status = "Success"

			self.save()
			return False

		"""
		Agent Update Server Status

		Start State -> Pending
		Running State -> Running, Rolling Back, Failure

		Terminating State -> (Success / Rolled Back + Agent Status need to be Active) or Fatal,
		"""

		# status: DF.Literal["Draft", "Pending", "Running", "Success", "Failure", "Fatal", "Skipped", "Rolling Back", "Rolled Back"]

		if current_agent_update_to_process.status == "Pending":
			"""
			If pending, run the ansible play to update the agent
			"""
			current_agent_update_to_process.status = "Running"
			self.save(ignore_version=True)
			return True

		if current_agent_update_to_process.status == "Running":
			if not current_agent_update_to_process.update_ansible_play:
				return False

			play_status = frappe.get_value(
				"Ansible Play", current_agent_update_to_process.update_ansible_play, "status"
			)
			if play_status in ("Success", "Failure"):
				current_agent_update_to_process.end = frappe.utils.now_datetime()
				current_agent_update_to_process.status = play_status
				self.save(ignore_version=True)

			return False

		if current_agent_update_to_process.status == "Failure":
			current_agent_update_to_process.status = "Rolling Back"
			self.save(ignore_version=True)
			return True

		if current_agent_update_to_process.status == "Rolling Back":
			if not current_agent_update_to_process.rollback_ansible_play:
				return False

			play_status = frappe.get_value(
				"Ansible Play", current_agent_update_to_process.rollback_ansible_play, "status"
			)
			if play_status == "Success":
				current_agent_update_to_process.status = "Rolled Back"
				current_agent_update_to_process.end = frappe.utils.now_datetime()
				self.save(ignore_version=True)
			elif play_status == "Failure":
				current_agent_update_to_process.status = "Fatal"
				self.save(ignore_version=True)

			return False

		if (
			current_agent_update_to_process.status == "Success"
			or current_agent_update_to_process.status == "Rolled Back"
		):
			agent = Agent(
				current_agent_update_to_process.server,
				server_type=current_agent_update_to_process.server_type,
			)
			message = ""
			with contextlib.suppress(Exception):
				message = agent.ping()

			if not current_agent_update_to_process.status_check_started_on:
				current_agent_update_to_process.status_check_started_on = frappe.utils.now_datetime()

			if message == "pong":
				current_agent_update_to_process.agent_status = "Active"
			else:
				current_agent_update_to_process.agent_status = "Inactive"

			# Check if agent status check timedout
			if (
				current_agent_update_to_process.agent_status == "Inactive"
				and (
					frappe.utils.now_datetime() - current_agent_update_to_process.status_check_started_on
				).total_seconds()
				> self.agent_startup_timeout_minutes * 60
			):
				# TODO: add reason why status changes in doctype
				if current_agent_update_to_process.status == "Success":
					current_agent_update_to_process.status = "Failure"
				else:
					current_agent_update_to_process.status = "Fatal"

			self.save()

		return False

	def _update_agent_on_server(self):
		current_agent_update_to_process = self.current_agent_update_to_process
		server_doc = frappe.get_doc(
			current_agent_update_to_process.server_type, current_agent_update_to_process.server
		)

		is_rollback = False
		if current_agent_update_to_process.status == "Rolling Back":
			is_rollback = True
		commit = self.commit_hash
		if is_rollback:
			commit = current_agent_update_to_process.rollback_commit

		play = Ansible(
			playbook="update_agent.yml",
			variables={
				"agent_repository_url": self.agent_repository_url,
				"agent_repository_branch_or_commit_ref": f"upstream/{commit}",
				"agent_update_args": self.agent_update_args,
			},
			server=server_doc,
			user=server_doc._ssh_user(),
			port=server_doc._ssh_port(),
		)

		data_to_update = {
			"start": frappe.utils.now_datetime(),
		}

		if is_rollback:
			data_to_update["rollback_ansible_play"] = play.play
		else:
			data_to_update["update_ansible_play"] = play.play

		frappe.db.set_value(
			"Agent Update Server",
			current_agent_update_to_process.name,
			data_to_update,
			update_modified=False,
		)
		frappe.db.commit()

		play.run()

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
		date_limit = datetime.datetime(
			2025,
			4,
			26,
			hour=15,
			minute=9,
			second=0,
		)
		commit_date = self.fetch_commit_date(ref)
		if commit_date is not None and commit_date >= date_limit:
			return True
		return False


def process_bulk_agent_update():
	agent_update_names = frappe.get_all("Agent Update", filters={"status": "Running"}, pluck="name")
	for agent_update_name in agent_update_names:
		try:
			doc: AgentUpdate = frappe.get_doc("Agent Update", agent_update_name)
			doc.execute()
		except Exception as e:
			frappe.log_error(
				title=f"Agent Update {agent_update_name} failed to process",
				message=str(e),
				reference_doctype="Agent Update",
				reference_name=agent_update_name,
			)
