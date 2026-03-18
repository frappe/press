# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import json
import time
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime
from rq.timeouts import JobTimeoutException

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import create_platform_build_and_deploy
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	import datetime
	from collections.abc import Callable

	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.server.server import Server
	from press.press.doctype.site.site import Site
	from press.press.doctype.site_action_step.site_action_step import SiteActionStep
	from press.press.doctype.site_migration.site_migration import SiteMigration
	from press.press.doctype.site_update.site_update import SiteUpdate


class StepType:
	Validation = "Validation"
	Preparation = "Preparation"
	Main = "Main"


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
			"Move From Private To Shared Bench",
			"Move Site To Different Server / Bench",
			"Move Site To Different Region",
		]
		arguments: DF.SmallText
		destination_bench: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		scheduled_time: DF.Datetime | None
		site: DF.Link
		start: DF.Datetime | None
		status: DF.Literal["Scheduled", "Cancelled", "Running", "Failure", "Success"]
		steps: DF.Table[SiteActionStep]
		team: DF.Link
	# end: auto-generated types

	current_step: SiteActionStep | None = None

	dashboard_fields = ("action_type", "scheduled_time", "site", "status", "start", "end", "duration")

	def get_steps_for_action(self) -> list[tuple[Callable, str]]:
		if self.action_type == "Move Site To Different Region":
			return [
				(self.pre_validate_move_site_to_different_cluster, StepType.Validation),
				(self.process_move_site_to_different_cluster, StepType.Main),
			]

		if self.action_type == "Move Site To Different Server / Bench":
			return [
				(self.pre_validate_move_site_to_different_server, StepType.Validation),
				(self.clone_and_create_bench_group, StepType.Preparation),
				(self.move_site_to_bench_group, StepType.Main),
			]

		return []

	def pre_validate_move_site_to_different_server(self):
		"""Pre Validate Move Site To Different Server / Bench"""

		current_bench: Bench = frappe.get_doc("Bench", self.site_doc.bench)
		current_release_group: ReleaseGroup = frappe.get_doc("Release Group", current_bench.group)
		destination_server = self.get_argument("destination_server", current_bench.server)
		self.set_argument("destination_server", destination_server)

		server: Server = frappe.get_doc("Server", destination_server)
		if not server.public and not server.has_permission("write"):
			frappe.throw(f"You don't have permission to deploy on server {server.name}")

		if self.get_argument("destination_release_group"):
			# Existing bench chosen - validate the release group
			if frappe.db.get_value("Release Group", self.get_argument("destination_release_group"), "public"):
				frappe.throw(
					f"Release Group {self.get_argument('destination_release_group')} is a public release group. Please select a different release group."
				)
			self._validate_apps_in_release_group(self.get_argument("destination_release_group"))
		elif not self.get_argument("new_release_group_name"):
			# No destination group and no new name provided - auto-generate
			if current_release_group.public:
				self.set_argument("new_release_group_name", current_release_group.title + " - Clone")
			else:
				# Private group - add the destination server to the current group if needed
				if not any(s.server == destination_server for s in current_release_group.servers):
					current_release_group.append(
						"servers",
						{"server": destination_server, "default": False},
					)
					current_release_group.save()
				self.set_argument("destination_release_group", current_release_group.name)

	def clone_and_create_bench_group(self):  # noqa
		"""Clone and Create Private Bench"""
		if self.get_argument("destination_release_group") and not self.current_step.reference_name:
			current_cluster = self.site_doc.cluster

			filters = {
				"group": self.get_argument("destination_release_group"),
				"status": "Active",
			}

			if self.get_argument("destination_server"):
				filters["server"] = self.get_argument("destination_server")
			else:
				filters["cluster"] = current_cluster

			# Find out the destination_bench based on
			# - destination release group + destination server (if provided) OR
			# - destination release group + current cluster (if destination server is not provided)
			# If there is an active bench, set it and move to next step
			bench = frappe.db.get_value("Bench", filters, "name")
			if bench:
				self.set_argument("destination_bench", bench)
				return StepStatus.Skipped

		is_new_build_trigerred = (
			self.current_step.reference_doctype == "Deploy Candidate Build"
			and self.current_step.reference_name
		)

		if not is_new_build_trigerred:
			# If there is no active bench found, try to create a new bench
			site: Site = frappe.get_doc("Site", self.site)
			current_group: ReleaseGroup = frappe.get_doc("Release Group", site.group)
			new_group: ReleaseGroup | None = None

			# If destination release group is provided, we will use that release group
			if self.get_argument("destination_release_group"):
				new_group: ReleaseGroup = frappe.get_doc(
					"Release Group", self.get_argument("destination_release_group")
				)
				requested_destination_server = self.get_argument("destination_server", site.server)
				if requested_destination_server and not any(
					server.server == requested_destination_server for server in new_group.servers
				):
					new_group.append(
						"servers",
						{"server": requested_destination_server, "default": False},
					)
					new_group.save()

				self.set_argument("destination_server", requested_destination_server)

			# Else, we will clone current release group
			else:
				new_group_title = self._ensure_no_duplicate_release_group_title(
					self.get_argument("new_release_group_name") or f"{site.group} - Cloned"
				)
				new_group: ReleaseGroup = frappe.new_doc("Release Group")
				new_group.update(
					{
						"title": new_group_title,
						"team": self.team,
						"public": 0,
						"enabled": 1,
						"version": current_group.version,
						"dependencies": current_group.dependencies,
						"is_redisearch_enabled": current_group.is_redisearch_enabled,
					}
				)

				new_group.append(
					"servers",
					{"server": self.get_argument("destination_server", site.server), "default": True},
				)

				# Add apps to rg if they are installed in site
				apps_installed_in_site = [app.app for app in site.apps]
				for i in [app for app in current_group.apps if app.app in apps_installed_in_site]:
					new_group.append("apps", i)

				counter = 1
				while True:
					try:
						new_group.insert()
						break
					except frappe.UniqueValidationError as e:
						# If there is a unique validation error, it means that there is already a release group with same name. So, we will append a counter to the name and try again.
						new_group.title = f"{new_group_title} {counter}"
						counter += 1

						if counter > 100:
							# Ideally this should never happen
							# but to avoid infinite loop, we will break after 100 attempts and raise the error
							raise e

			# Set essential arguments for next steps
			self.set_argument("destination_server", self.get_argument("destination_server", site.server))
			self.set_argument("destination_release_group", new_group.name)
			server: Server = frappe.get_doc("Server", self.get_argument("destination_server"))

			# Create deploy candidate and schedule build and deploy
			deploy_candidate = new_group.create_deploy_candidate()
			deploy_candidate_build_name = create_platform_build_and_deploy(
				deploy_candidate=deploy_candidate.name,
				server=server.name,
				platform=server.platform,
			)

			self.set_argument("new_deploy_candidate", deploy_candidate.name)
			self.set_argument("new_deploy_candidate_build", deploy_candidate_build_name)

			self.current_step.reference_doctype = "Deploy Candidate Build"
			self.current_step.reference_name = deploy_candidate_build_name

			return StepStatus.Running

		# Check status of created deploy candidate build
		build: DeployCandidateBuild = frappe.get_doc(
			"Deploy Candidate Build",
			self.current_step.reference_name,
		)
		if build.status == "Failure":
			self._archive_newly_created_release_group()
			return StepStatus.Failure

		if build.status != "Success":
			return StepStatus.Running

		# If build is success, check for deployed bench
		bench_name = frappe.db.get_value(
			"Bench",
			{
				"build": build.name,
				"candidate": build.deploy_candidate,
				"server": self.get_argument("destination_server"),
			},
		)
		if not bench_name:
			# If there is no bench created, assume it's still in progress
			return StepStatus.Running

		self.set_argument("new_bench", bench_name)

		bench_status = frappe.db.get_value("Bench", bench_name, "status")
		if bench_status == "Active":
			self.set_argument("destination_bench", bench_name)
			return StepStatus.Success

		if bench_status in ("Failure", "Archived", "Broken"):
			self._archive_newly_created_release_group()
			return StepStatus.Failure

		return StepStatus.Running

	def move_site_to_bench_group(self):  # noqa: C901
		"""Move Site to Bench Group"""

		if self.current_step.reference_doctype and self.current_step.reference_name:
			if self.current_step.reference_doctype == "Site Update":
				status = None
				doc: SiteUpdate = frappe.get_doc("Site Update", self.current_step.reference_name)
				if doc.status == "Success":
					status = StepStatus.Success
				elif doc.status == "Fatal" or doc.status == "Failure" or doc.status == "Recovered":
					status = StepStatus.Failure
				else:
					status = StepStatus.Running

			elif self.current_step.reference_doctype == "Site Migration":
				doc: SiteMigration = frappe.get_doc("Site Migration", self.current_step.reference_name)

				if doc.status == "Success":
					status = StepStatus.Success

				elif doc.status == "Failure":
					status = StepStatus.Failure

				else:
					status = StepStatus.Running

			else:
				raise Exception(f"Unknown reference doctype {self.current_step.reference_doctype}")

			if status is None:
				raise Exception("Status cannot be None")

			if status == StepStatus.Failure:
				self._archive_newly_created_release_group()

			return status

		# Check if destination bench is on same server
		destination_bench: Bench = frappe.get_doc("Bench", self.get_argument("destination_bench"))
		current_bench: Bench = frappe.get_doc("Bench", self.site_doc.bench)

		doc = None

		# We are scheduling the site migration/update for 1 minute later
		# to ensure that if there are any pending/running jobs running
		# the update / migration will be picked up after those jobs are completed
		scheduled_time = add_to_date(minutes=1)

		if current_bench.server != destination_bench.server:
			# Create site migration
			doc = frappe.get_doc(
				{
					"doctype": "Site Migration",
					"site": self.site,
					"destination_group": destination_bench.group,
					"destination_bench": destination_bench.name,
					"destination_server": destination_bench.server,
					"destination_cluster": destination_bench.cluster,
					"status": "Scheduled",
					"scheduled_time": scheduled_time,
					"skip_failing_patches": self.get_argument("skip_failing_patches", False),
				}
			).insert()

			with contextlib.suppress(Exception):
				doc.start()
		else:
			# Create site update
			doc = frappe.get_doc(
				{
					"doctype": "Site Update",
					"site": self.site,
					"destination_group": destination_bench.group,
					"destination_bench": destination_bench.name,
					"status": "Scheduled",
					"scheduled_time": scheduled_time,
					"skipped_failing_patches": self.get_argument("skip_failing_patches", False),
					"skipped_backups": False,
					"ignore_past_failures": True,
				}
			).insert()

			with contextlib.suppress(Exception):
				doc.start()

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
		current_group = frappe.db.get_value("Site", self.site, "group")
		bench_vals = frappe.db.get_value(
			"Bench",
			{"group": current_group, "cluster": target_cluster, "status": "Active"},
			["name", "server"],
		)

		if bench_vals is None:
			frappe.throw(f"Bench {current_group} does not have an existing deploy in {target_cluster}")

		bench, server = bench_vals

		site_migration: SiteMigration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": self.site,
				"destination_group": current_group,
				"destination_bench": bench,
				"destination_server": server,
				"destination_cluster": target_cluster,
				"scheduled_time": self.scheduled_time_formatted,
				"skip_failing_patches": self.get_argument("skip_failing_patches", False),
			}
		).insert()

		self.set_argument("site_migration", site_migration.name)

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

	def _archive_newly_created_release_group(self):
		# If Release Group is 'Awaiting Deploy'
		from press.press.doctype.release_group.release_group import get_status

		# Try to remove it
		with contextlib.suppress(frappe.DoesNotExistError):
			release_group_name = self.get_argument("destination_release_group")
			if release_group_name and get_status(release_group_name) == "Awaiting Deploy":
				release_group: ReleaseGroup = frappe.get_doc("Release Group", release_group_name)
				release_group.archive()

	def get_press_error_notifications(self) -> list[dict]:  # noqa: C901
		if self.status != "Failure":
			return []

		notifications = []
		for step in self.steps:
			if step.status != "Failure":
				continue
			if not step.reference_doctype or not step.reference_name:
				continue
			if step.reference_doctype == "Deploy Candidate Build":
				notifications.extend(
					frappe.get_all(
						"Press Notification",
						filters={
							"team": self.team,
							"type": "Bench Deploy",
							"document_type": step.reference_doctype,
							"document_name": step.reference_name,
							"class": "Error",
							"is_actionable": True,
						},
						fields=["title", "name"],
					)
				)

			elif step.reference_doctype == "Site Update":
				agent_jobs = []
				site_update_doc: SiteUpdate = frappe.get_doc(step.reference_doctype, step.reference_name)
				if site_update_doc.update_job:
					agent_jobs.append(site_update_doc.update_job)
				if site_update_doc.recover_job:
					agent_jobs.append(site_update_doc.recover_job)

				if agent_jobs:
					notifications.extend(
						frappe.get_all(
							"Press Notification",
							filters={
								"team": self.team,
								"type": "Site Update",
								"document_type": "Agent Job",
								"document_name": ("in", agent_jobs),
								"class": "Error",
								"is_actionable": True,
							},
							fields=["title", "name"],
						)
					)

		return notifications

	# Internal

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

	def before_insert(self):
		# Check if no other site action is running for the same site
		if frappe.db.exists(
			"Site Action",
			{
				"site": self.site,
				"status": ("not in", ["Success", "Failure", "Cancelled"]),
			},
		):
			frappe.throw(
				"Another site action is already scheduled / running for this site. Please wait for it to complete before starting a new one."
			)

		# If any key is blank string or None, remove it from arguments
		args = self.arguments_dict
		cleaned_args = {k: v for k, v in args.items() if v not in ("", None)}
		self.arguments = json.dumps(cleaned_args, indent=2)

	def after_insert(self):
		self.add_steps()
		self.run_pre_validation_steps()
		self.save()

		# Run Preparation steps after insert
		if self.scheduled_time_formatted and self.is_preparation_steps_pending_or_running():
			self.execute()

	def validate(self):
		if self.action_type == "Move From Private To Shared Bench":
			frappe.throw("Move From Private To Shared Bench action is not available currently.")

	def on_update(self):
		save_doc = False
		if self.has_value_changed("status"):
			if self.status == "Running" and not self.start:
				self.start = now_datetime()
				save_doc = True

			elif self.status in ["Success", "Failure"] and not self.end:
				self.end = now_datetime()
				if self.start:
					self.duration = int((self.end - self.start).total_seconds())
				save_doc = True

		if save_doc:
			self.save()

	def run_pre_validation_steps(self):
		steps = self.get_steps_for_action()
		for method, step_type in steps:
			if step_type != StepType.Validation:
				continue

			method()

	@property
	def scheduled_time_formatted(self) -> datetime.datetime | None:
		return frappe.utils.data.get_datetime(self.scheduled_time) if self.scheduled_time else None

	@property
	def arguments_dict(self):
		return json.loads(self.arguments) if self.arguments else {}

	def get_argument(self, key: str, default=None):
		args = self.arguments_dict
		return args.get(key, default)

	def set_argument(self, key: str, value) -> None:
		if key == "destination_bench":
			self.destination_bench = value

		args = self.arguments_dict
		args[key] = value
		self.arguments = json.dumps(args, indent=2)

	@cached_property
	def site_doc(self) -> Site:
		return frappe.get_doc("Site", self.site)

	def get_doc(self, doc):
		doc.arguments_dict = self.arguments_dict
		doc.steps = self.get_steps()
		doc.errors = self.get_press_error_notifications()
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

	@dashboard_whitelist()
	def start_now(self):
		self.scheduled_time = None
		self.save()

		self.execute()

	@dashboard_whitelist()
	def cancel_action(self):
		if self.status != "Scheduled":
			frappe.throw("Only Scheduled actions can be cancelled.")
			return

		self.status = "Cancelled"
		for step in self.steps:
			if step.status in ("Pending", "Running"):
				step.status = "Skipped"

		if self.action_type == "Move Site To Different Region":
			site_migration_name = self.get_argument("site_migration")
			if site_migration_name and frappe.db.exists("Site Migration", site_migration_name):
				status = frappe.db.get_value("Site Migration", site_migration_name, "status", for_update=True)
				if status != "Scheduled":
					frappe.throw(
						"Site Migration is already in progress. Cannot cancel the action.",
						frappe.ValidationError,
					)
					return

				frappe.delete_doc("Site Migration", site_migration_name, ignore_permissions=True)

		self.save(ignore_version=True)

	@frappe.whitelist()
	def execute(self):
		if (
			self.status == "Scheduled"
			and self.scheduled_time_formatted
			and self.scheduled_time_formatted > now_datetime()
			and not self.is_preparation_steps_pending_or_running()
		):
			# Not yet time to execute
			return

		self.next()

	def execute_step(self, step_name):
		# frappe.set_user(self.owner)
		# frappe.local._current_team = frappe.get_cached_doc("Team", self.team)

		if self.status == "Cancelled":
			return

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

		except Exception as e:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)
			step.error_message = str(e)

		step.end = now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure":
			self.fail(save=False)

		self.save(ignore_version=True)
		# TODO: need optimization
		# Some callback, else will take lot of resources

		if frappe.flags.disable_auto_enqueue_next_step:
			return

		self.next()

	def fail(self, save: bool = True) -> None:
		self.status = "Failure"
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Skipped"
		if save:
			self.save(ignore_version=True)

	def finish(self) -> None:
		# if status is already Success or Failure, then don't update the status and durations
		if self.status not in ("Success", "Failure"):
			self.status = "Success" if (self.is_preparation_steps_successful() and self) else "Failure"

		self.save()

	def next(self) -> None:
		if (
			self.status != "Running"
			and self.status not in ("Success", "Failure")
			and not (
				self.status == "Scheduled"
				and self.scheduled_time_formatted
				and self.scheduled_time_formatted > now_datetime()
			)
		):
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

		if (
			self.status == "Scheduled"
			and self.scheduled_time_formatted
			and self.scheduled_time_formatted > now_datetime()
		) and not self.is_preparation_steps_pending_or_running():
			return

		if self.status == "Cancelled":
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"execute_step",
			step_name=next_step_to_run.name,
			enqueue_after_commit=True,
			job_id=f"site_action||execute_step||{self.name}",
			deduplicate=True,
		)

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
		return self.is_preparation_steps_successful() and self.is_main_steps_successful()

	def is_preparation_steps_successful(self) -> bool:
		return all(
			step.status in ("Skipped", "Success") for step in self.steps if step.step_type == "Preparation"
		)

	def is_main_steps_successful(self) -> bool:
		return all(step.status in ("Skipped", "Success") for step in self.steps if step.step_type == "Main")

	def is_preparation_steps_pending_or_running(self) -> bool:
		return any(
			step.status in ("Pending", "Running") for step in self.steps if step.step_type == "Preparation"
		)

	def _validate_apps_in_release_group(self, release_group_name: str) -> None:
		destination_release_group: ReleaseGroup = frappe.get_doc("Release Group", release_group_name)
		rg_apps = set(app.app for app in destination_release_group.apps)
		site_apps = set(app.app for app in self.site_doc.apps)
		# Remove frappe from site_apps
		rg_apps.discard("frappe")
		site_apps.discard("frappe")
		if diff := site_apps - rg_apps:
			frappe.throw(
				f"Site has following apps {', '.join(diff)} which are not present in the destination release group. Please install those apps in the destination release group or remove them from the site before moving.",
				frappe.ValidationError,
			)

	def _ensure_no_duplicate_release_group_title(self, name: str) -> str:
		if not name:
			return frappe.generate_hash(length=10)

		while True:
			if not frappe.db.exists(
				"Release Group",
				{
					"team": self.team,
					"title": name,
					"enabled": True,
				},
			):
				return name
			name = f"{name} - {frappe.generate_hash(length=5)}"


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site Action")


# Utility functions


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
