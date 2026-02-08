# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import time
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from rq.timeouts import JobTimeoutException

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from collections.abc import Callable

	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.site.site import Site
	from press.press.doctype.site_action_step.site_action_step import SiteActionStep
	from press.press.doctype.site_update.site_update import SiteUpdate


class StepType:
	Validation = "Validation"
	Preparation = "Preparation"
	Main = "Main"
	Cleanup = "Cleanup"


class StepStatus:
	Pending = "Pending"
	Scheduled = "Scheduled"
	Running = "Running"
	Skipped = "Skipped"
	Success = "Success"
	Failure = "Failure"


class SiteAction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site_action_step.site_action_step import SiteActionStep

		action_type: DF.Literal[
			"Move From Shared To Private Bench",
			"Move From Private To Shared Bench",
			"Move Site To Different Server",
			"Move Site To Different Region",
		]
		arguments: DF.SmallText
		scheduled_time: DF.Datetime | None
		site: DF.Link
		status: DF.Literal["Scheduled", "Cancelled", "Running", "Failure", "Success"]
		steps: DF.Table[SiteActionStep]
		team: DF.Link
	# end: auto-generated types

	current_step: SiteActionStep | None = None

	dashboard_fields = (
		"action_type",
		"scheduled_time",
		"site",
		"status",
	)

	def get_steps_for_action(self) -> list[tuple[Callable, str]]:
		if self.action_type == "Move From Shared To Private Bench":
			return [
				(self.pre_validate_move_site_from_shared_to_private_bench, StepType.Validation),
				(self.clone_and_create_bench_group, StepType.Preparation),
				(self.move_site_to_bench_group, StepType.Main),
			]

		if self.action_type == "Move Site To Different Region":
			return [
				(self.pre_validate_move_site_to_different_cluster, StepType.Validation),
				(self.process_move_site_to_different_cluster, StepType.Main),
			]

		if self.action_type == "Move Site To Different Server":
			return [
				(self.pre_validate_move_site_to_different_server, StepType.Validation),
				(self.clone_and_create_bench_group, StepType.Preparation),
				(self.move_site_to_bench_group, StepType.Main),
			]

		return []

	def pre_validate_move_site_to_different_server(self):
		"""Pre Validate Move Site To Different Server"""

		# If public bench, just clone the bench group with `- Clone` suffix and deploy bench there
		# Else, add the server in release group. Trigger a re-deploy and move the site there.

		current_bench: Bench = frappe.get_doc("Bench", self.site_doc.bench)
		if current_bench.public:
			self.set_argument("new_release_group_name", current_bench.group + " - Clone")
		else:
			release_group: ReleaseGroup = frappe.get_doc("Release Group", current_bench.group)
			# Check if current server exists in release group
			destination_server = self.get_argument("destination_server")

			if not any(server.server == destination_server for server in release_group.servers):
				dcb_name = release_group.add_server(destination_server, deploy=True, force_new_build=True)
				dcb: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dcb_name)

				self.set_argument("destination_server", dcb.server)
				self.set_argument("cloned_release_group", release_group.name)
				self.set_argument("cloned_deploy_candidate", dcb.candidate)
				self.set_argument("cloned_deploy_candidate_build", dcb_name)

	def pre_validate_move_site_from_shared_to_private_bench(self):
		"""Pre Validate Move Site From Shared To Private Bench"""
		if not self.get_argument("destination_release_group"):
			return

		if frappe.db.get_value("Release Group", self.get_argument("destination_release_group"), "public"):
			frappe.throw(
				f"Release Group {self.get_argument('destination_release_group')} is a public release group. Please select a different release group."
			)

	def clone_and_create_bench_group(self):  # noqa
		"""Clone and Create Private Bench"""
		if self.get_argument("destination_release_group"):
			current_cluster = frappe.db.get_value("Server", self.site_doc.server, "cluster")

			filters = {
				"group": self.get_argument("destination_release_group"),
				"status": "Active",
			}

			if self.get_argument("destination_server"):
				filters["server"] = self.get_argument("destination_server")
			else:
				filters["cluster"] = current_cluster

			# find out the destination_bench based on the destination_release_group and
			self.set_argument("destination_bench", frappe.db.get_value("Bench", filters, "name"))
			return StepStatus.Skipped

		if (
			self.current_step.reference_doctype == "Deploy Candidate Build"
			and self.current_step.reference_name
		):
			# Check build status
			build: DeployCandidateBuild = frappe.get_doc(
				"Deploy Candidate Build",
				self.current_step.reference_name,
			)
			if build.status == "Failure":
				return StepStatus.Failure

			if build.status != "Success":
				return StepStatus.Running

			# If build is success, check for deployed bench
			bench_name = frappe.db.get_value(
				"Bench",
				{
					"build": build.name,
					"candidate": self.get_argument("cloned_deploy_candidate"),
					"server": self.get_argument("destination_server"),
				},
			)
			if not bench_name:
				return StepStatus.Running

			self.set_argument("cloned_bench", bench_name)

			# If deployed bench is success, return Success
			bench_status = frappe.db.get_value("Bench", bench_name, "status")
			if bench_status == "Active":
				self.set_argument("destination_release_group", self.get_argument("cloned_release_group"))
				self.set_argument("destination_bench", bench_name)
				return StepStatus.Success
			if bench_status in ("Failure", "Archived", "Broken"):
				return StepStatus.Failure
			return StepStatus.Running

		site = frappe.get_doc("Site", self.site)
		group = frappe.get_doc("Release Group", site.group)
		cloned_group = frappe.new_doc("Release Group")

		cloned_group.update(
			{
				"title": self.get_argument("new_release_group_name") or f"{site.group} - Cloned",
				"team": self.team,
				"public": 0,
				"enabled": 1,
				"version": group.version,
				"dependencies": group.dependencies,
				"is_redisearch_enabled": group.is_redisearch_enabled,
				"servers": [
					{"server": self.get_argument("destination_server", site.server), "default": False}
				],
			}
		)

		# add apps to rg if they are installed in site
		apps_installed_in_site = [app.app for app in site.apps]
		cloned_group.apps = [app for app in group.apps if app.app in apps_installed_in_site]

		cloned_group.insert()

		candidate = cloned_group.create_deploy_candidate()
		cloned_deploy_candidate_build = candidate.schedule_build_and_deploy()

		self.set_argument("destination_server", site.server)
		self.set_argument("cloned_release_group", cloned_group.name)
		self.set_argument("cloned_deploy_candidate", candidate.name)
		self.set_argument("cloned_deploy_candidate_build", cloned_deploy_candidate_build["name"])

		self.current_step.reference_doctype = "Deploy Candidate Build"
		self.current_step.reference_name = cloned_deploy_candidate_build["name"]

		return StepStatus.Running

	def move_site_to_bench_group(self):
		"""Move Site to Bench Group"""
		if self.current_step.reference_doctype == "Site Update" and self.current_step.reference_name:
			# Site Update is already scheduled
			doc: SiteUpdate = frappe.get_doc("Site Update", self.current_step.reference_name)
			if doc.status == "Success":
				return StepStatus.Success
			if doc.status == "Fatal" or doc.status == "Failure" or doc.status == "Recovered":
				return StepStatus.Failure

			return StepStatus.Running

		# Check if destination release group is on same server
		destination_bench: Bench = frappe.get_doc("Bench", self.get_argument("destination_bench"))
		current_bench: Bench = frappe.get_doc("Bench", self.site_doc.bench)

		doc = None
		if current_bench.server != destination_bench.server:
			# Create site migration
			doc = self.site_doc.move_to_bench(
				self.get_argument("destination_bench"),
				skip_failing_patches=self.get_argument("skip_failing_patches", False),
			)
		else:
			# Create site update
			doc = self.site_doc.move_to_group(
				self.get_argument("destination_release_group"),
				skip_failing_patches=self.get_argument("skip_failing_patches", False),
				skip_backups=self.get_argument("skip_backups", False),
			)

		self.current_step.reference_doctype = doc.doctype
		self.current_step.reference_name = doc.name
		self.save()
		return StepStatus.Running

	# Move Site to Different Cluster
	def pre_validate_move_site_to_different_cluster(self):
		"""Pre Validate Move Site To Different Cluster"""
		# validate if the target cluster is different from current cluster
		target_cluster = self.get_argument("cluster")
		current_cluster = frappe.db.get_value("Server", self.site_doc.server, "cluster")
		if target_cluster == current_cluster:
			frappe.throw("Target cluster must be different from current cluster.")

		# create the `Site Migration`
		doc = self.site_doc.change_region(
			cluster=target_cluster,
			scheduled_time=self.scheduled_time,
			skip_failing_patches=self.get_argument("skip_failing_patches", False),
		)
		self.set_argument("site_migration", doc.name)

	def process_move_site_to_different_cluster(self):
		"""Move Site To Different Cluster"""
		if self.current_step.reference_doctype == "Site Migration" and self.current_step.reference_name:
			# Site Migration is already scheduled
			doc = frappe.get_doc("Site Migration", self.current_step.reference_name)
			if doc.status == "Success":
				return StepStatus.Success
			if doc.status == "Failure":
				return StepStatus.Failure
			return StepStatus.Running

		self.current_step.reference_doctype = "Site Migration"
		self.current_step.reference_name = self.get_argument("site_migration")
		return StepStatus.Running

	def pre_validate_schedule_site_update(self):
		"""Schedule Site Update"""
		args = self.arguments_dict
		doc: SiteUpdate = frappe.get_doc(
			{
				"doctype": "Site Update",
				"site": self.site,
				"backup_type": "Physical" if args.get("physical_backup", False) else "Logical",
				"skipped_failing_patches": args.get("skip_failing_patches", False),
				"skipped_backups": args.get("skip_backups", False),
				"status": "Scheduled" if self.scheduled_time else "Pending",
				"scheduled_time": self.scheduled_time,
			}
		).insert()
		self.set_argument("site_update", doc.name)

	def add_steps(self):
		self.steps = []
		for method, step_type in self.get_steps_for_action():
			if step_type == StepType.Validation:
				continue

			self.append(
				"steps",
				{
					"step": method.__doc__,
					"method": method.__name__,
					"step_type": step_type,
				},
			)

	def validate(self):
		if self.action_type == "Move From Private To Shared Bench":
			frappe.throw("Move From Private To Shared Bench action is not available currently.")

	def after_insert(self):
		self.add_steps()
		self.run_pre_validation_steps()
		self.save()

	def run_pre_validation_steps(self):
		steps = self.get_steps_for_action()
		for method, step_type, _ in steps:
			if step_type != StepType.Validation:
				continue

			method()

	@property
	def arguments_dict(self):
		return json.loads(self.arguments) if self.arguments else {}

	def get_argument(self, key: str, default=None):
		args = self.arguments_dict
		return args.get(key, default)

	def set_argument(self, key: str, value) -> None:
		args = self.arguments_dict
		args[key] = value
		self.arguments = json.dumps(args, indent=2)

	@cached_property
	def site_doc(self) -> Site:
		return frappe.get_doc("Site", self.site)

	def get_doc(self, doc):
		doc.steps = self.get_steps()
		return doc

	def get_steps(self):
		"""
		Iterate over the steps and prepare a list of steps.
		If the step has a reference doctype, look if it has `get_steps` function, that will return their steps
			- Insert the steps
		{
			"name": "random_id",
			"title": "<title for the stage>",
			"status": "Skipped",
			"output": "<output or traceback>",
			"stage": "<group>",
		}
		"""
		frappe.flags.site_action_args = self.arguments_dict
		data = []
		for step in self.steps:
			data.extend(step.get_steps())

		return data

	def execute(self):
		if self.status == "Scheduled" and self.scheduled_time and self.scheduled_time > now_datetime():
			# Not yet time to execute
			return

		self.next()

	def execute_step(self, step_name):
		frappe.set_user(self.owner)
		frappe.local._current_team = frappe.get_cached_doc("Team", self.team)

		step = self.get_step(step_name)
		self.current_step = step

		if not step.start:
			step.start = now_datetime()
		try:
			result = getattr(self, step.method)()
			step.status = result
			"""
			If the step is sync and function is marked to wait for completion,
			Then wait for the function to complete
			"""
			if result == StepStatus.Running:
				step.attempts = step.attempts + 1 if step.attempts else 1
				time.sleep(1)

		except Exception:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure":
			self.fail(save=False)

		self.save(ignore_version=True)
		# TODO: need optimization
		# Some callback, else will take lot of resources
		self.next()

	def fail(self, save: bool = True) -> None:
		self.status = "Failure"
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Skipped"
		if save:
			self.save(ignore_version=True)
		self.cleanup()

	def finish(self) -> None:
		# if status is already Success or Failure, then don't update the status and durations
		if self.status not in ("Success", "Failure"):
			self.status = "Success" if (self.is_preparation_steps_successful() and self) else "Failure"

		self.cleanup_completed = self.is_cleanup_steps_successful()
		self.save()

	def next(self) -> None:
		if self.status != "Running" and self.status not in ("Success", "Failure"):
			self.status = "Running"
			self.save(ignore_version=True)

		next_step_to_run = None

		# Check if current_step is running
		current_running_step = self.current_running_step
		if current_running_step:
			next_step_to_run = current_running_step
		elif self.next_step:
			next_step_to_run = self.next_step

		if not next_step_to_run:
			# We've executed everything
			self.finish()
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"execute_step",
			step_name=next_step_to_run.name,
			enqueue_after_commit=True,
		)

	@frappe.whitelist()
	def cleanup(self):
		is_cleanup_required = False
		for step in self.steps:
			# Mark the pending non-cleanup steps as skipped
			if step.step_type != "Cleanup" and step.status == "Pending":
				step.status = "Skipped"

			# Mark the cleanup steps with non-failure status as pending
			if step.step_type == "Cleanup" and step.status != "Failure":
				step.status = "Pending"
				is_cleanup_required = True

		if is_cleanup_required:
			self.next()

	@property
	def current_running_step(self) -> SiteActionStep | None:
		for step in self.steps:
			if step.status == "Running":
				return step
		return None

	@property
	def next_step(self) -> SiteActionStep | None:
		for step in self.steps:
			if step.status == "Pending":
				return step
		return None

	def get_step_status(self, step_method: Callable) -> str:
		step = self.get_step_by_method(step_method.__name__)
		return step.status if step else "Pending"

	def get_step_by_method(self, method_name) -> SiteActionStep | None:
		for step in self.steps:
			if step.method == method_name:
				return step
		return None

	def get_step(self, step_name) -> SiteActionStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None

	def is_all_steps_successful(self) -> bool:
		return (
			self.is_preparation_steps_successful()
			and self.is_main_steps_successful()
			and self.is_cleanup_steps_successful()
		)

	def is_preparation_steps_successful(self) -> bool:
		return all(
			step.status in ("Skipped", "Success") for step in self.steps if step.step_type == "Preparation"
		)

	def is_main_steps_successful(self) -> bool:
		return all(step.status in ("Skipped", "Success") for step in self.steps if step.step_type == "Main")

	def is_cleanup_steps_successful(self) -> bool:
		return all(
			step.status in ("Skipped", "Success") for step in self.steps if step.step_type == "Cleanup"
		)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site Action")


# Utility functions


def move_site_from_shared_to_private_bench(
	site: str,
	server: str | None = None,
	new_release_group_name: str | None = None,
	skip_failing_patches: bool = False,
	scheduled_time: str | None = None,
) -> SiteAction:
	"""Schedule Move Site From Shared To Private Bench Action for a site"""
	action = frappe.get_all(
		"Site Action",
		filters={
			"site": site,
			"action_type": "Move From Shared To Private Bench",
			"status": ["in", ("Pending", "Running", "Scheduled")],
		},
		limit=1,
	)

	if action:
		# Move Site Action is already scheduled or running
		frappe.throw(
			f"Move Site From Shared To Private Bench is already scheduled or running for site {site}."
		)

	# ensure the server is public
	if server and not frappe.db.get_value("Server", server, "public"):
		frappe.throw(f"Server {server} is a public server. Please select a different server.")

	args = {
		"skip_failing_patches": skip_failing_patches,
		"new_release_group_name": new_release_group_name,
		"server": server,
	}

	log_site_activity(site, "Move From Shared To Private Bench")

	return frappe.get_doc(
		{
			"doctype": "Site Action",
			"site": site,
			"action_type": "Move From Shared To Private Bench",
			"arguments": json.dumps(args),
			"scheduled_time": scheduled_time,
		}
	).insert()  # type: ignore


def process_site_actions():
	site_actions = frappe.get_all(
		"Site Action",
		filters={
			"status": "Scheduled",
			"scheduled_time": ["<=", now_datetime()],
		},
	)
	site_actions_without_scheduled_time = frappe.get_all(
		"Site Action",
		filters={
			"status": "Scheduled",
			"scheduled_time": None,
		},
	)
	running_site_actions = frappe.get_all(
		"Site Action",
		filters={
			"status": "Running",
		},
	)

	site_actions.extend(site_actions_without_scheduled_time)
	site_actions.extend(running_site_actions)

	for site_action in site_actions:
		if has_job_timeout_exceeded():
			return
		try:
			doc: SiteAction = frappe.get_doc("Site Action", site_action.name)
			doc.execute()
			frappe.db.commit()
		except JobTimeoutException:
			frappe.db.rollback()
			return
		except Exception:
			frappe.db.rollback()
