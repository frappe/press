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

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from collections.abc import Callable

	from press.press.doctype.site.site import Site
	from press.press.doctype.site_action_step.site_action_step import SiteActionStep
	from press.press.doctype.site_update.site_update import SiteUpdate


class StepType:
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
			"Update Site",
			"Move From Shared To Private Bench",
			"Move From Private To Shared Bench",
			"Move Site To Different Server",
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

	def get_steps_to_add(
		self,
	) -> list[tuple[Callable, str, bool]]:
		Wait = True  # noqa: F841
		NoWait = False

		if self.action_type == "Update Site":
			return [
				(self.schedule_site_update, StepType.Main, NoWait),
			]

		return []

	def schedule_site_update(self):
		"""Schedule Site Update"""
		if self.current_step.reference_doctype == "Site Update" and self.current_step.reference_name:
			# Site Update is already scheduled
			doc: SiteUpdate = frappe.get_doc("Site Update", self.current_step.reference_name)
			if doc.status == "Success":
				return StepStatus.Success
			if doc.status == "Fatal" or doc.status == "Failure":
				return StepStatus.Failure

			if doc.status in (
				"Pending",
				"Running",
				"Scheduled",
				"Recovering",
			):
				return StepStatus.Running

		args = self.arguments_dict
		site_update_doc = frappe.get_doc(
			{
				"doctype": "Site Update",
				"site": self.site,
				"backup_type": "Physical" if args.get("physical_backup", False) else "Logical",
				"skipped_failing_patches": args.get("skip_failing_patches", False),
				"skipped_backups": args.get("skip_backups", False),
				"status": "Pending",
			}
		).insert()
		self.current_step.reference_doctype = site_update_doc.doctype
		self.current_step.reference_name = site_update_doc.name
		self.save()
		self.set_argument("site_update", site_update_doc.name)
		return StepStatus.Running

	def add_steps(self):
		self.steps = []
		for method, step_type, wait_for_completion in self.get_steps_to_add():
			self.append(
				"steps",
				{
					"step": method.__doc__,
					"method": method.__name__,
					"wait_for_completion": wait_for_completion,
					"step_type": step_type,
				},
			)

	def after_insert(self):
		self.add_steps()
		self.save()

	def validate(self):
		if not self.is_new():
			return
		pass

	def pre_validate_site_update(self):
		pass

	@property
	def arguments_dict(self):
		return json.loads(self.arguments) if self.arguments else {}

	def get_argument(self, key: str, default=None):
		args = self.arguments_dict
		return args.get(key, default)

	def set_argument(self, key: str, value) -> None:
		args = self.arguments_dict
		args[key] = value
		self.arguments = json.dumps(args)

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
		data = []
		for step in self.steps:
			data.extend(step.get_steps())

		return data

	def execute(self):
		if self.status == "Scheduled" and self.scheduled_time and self.scheduled_time > now_datetime():
			# Not yet time to execute
			return

		self.next()

	@dashboard_whitelist()
	def start_now(self):
		if self.status != "Scheduled":
			frappe.throw("Only Scheduled Site Actions can be started now.")
		self.scheduled_time = None
		self.save()

	@dashboard_whitelist()
	def cancel_action(self):
		if self.status not in ("Scheduled"):
			frappe.throw("Only Scheduled Site Actions can be cancelled.")
		self.status = "Cancelled"
		self.save()

	def execute_step(self, step_name):
		frappe.set_user(self.owner)

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
			if step.wait_for_completion and result == StepStatus.Running:
				step.attempts = step.attempts + 1 if step.attempts else 1
				self.save(ignore_version=True)
				time.sleep(1)

		except Exception:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure":
			self.fail(save=True)
		else:
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
			deduplicate=next_step_to_run.wait_for_completion
			is False,  # Don't deduplicate if wait_for_completion is True
			job_id=f"site_action||{self.name}||{next_step_to_run.name}",
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


def schedule_site_update(
	site: str,
	physical_backup: bool = False,
	skip_failing_patches: bool = False,
	skip_backups: bool = False,
	scheduled_time: str | None = None,
) -> SiteAction:
	"""Schedule Site Update Action for a site"""
	action = frappe.get_all(
		"Site Action",
		filters={
			"site": site,
			"action_type": "Update Site",
			"status": ["in", ("Pending", "Running", "Scheduled")],
		},
		limit=1,
	)

	if action:
		# Site Update Action is already scheduled or running
		frappe.throw(f"Site Update is already scheduled or running for site {site}.")

	args = {
		"physical_backup": physical_backup,
		"skip_failing_patches": skip_failing_patches,
		"skip_backups": skip_backups,
	}

	log_site_activity(site, "Update")

	return frappe.get_doc(
		{
			"doctype": "Site Action",
			"site": site,
			"action_type": "Update Site",
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
