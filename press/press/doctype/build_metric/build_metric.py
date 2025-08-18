# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import typing
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import median
from typing import Any

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from frappe.utils import DateTimeLikeObject

	from press.press.doctype.build_metric.build_metric_types import (
		ContextDurationType,
		DeployCandidateBuildType,
		DurationType,
		FailedBuildType,
		MetricsType,
	)


class BuildMetric(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		metric_dump: DF.JSON | None
		name: DF.Int | None
		start_from: DF.Datetime | None
		to: DF.Datetime | None
	# end: auto-generated types

	def after_insert(self):
		"""If dates not specified take last week"""
		self.start_from = self.start_from or frappe.utils.add_to_date(days=-7)
		self.to = self.to or frappe.utils.now()
		frappe.enqueue(self._get_metrics)

	def _get_metrics(self):
		build_metric = GenerateBuildMetric(self.start_from, self.to)
		build_metric.get_metrics()
		self.metric_dump = json.dumps(build_metric.dump_metrics(), indent=4)
		self.save()


@dataclass
class GenerateBuildMetric:
	from_date: DateTimeLikeObject
	end_date: DateTimeLikeObject
	metric_fields: list[str] = field(
		default_factory=lambda: [
			"name",
			"group",
			"status",
			"creation",
			"error_key",
			"retry_count",
			"build_output",
			"build_duration",
			"manually_failed",
			"pending_duration",
			"user_addressable_failure",
			"platform",
		]
	)

	def dump_metrics(self) -> MetricsType:
		return {
			"total_builds": self.total_builds,
			"total_failures": {
				"user_failure": len(self.total_failures["user_failure"]),
				"fc_manual_failure": len(self.total_failures["fc_manual_failure"]),
				"fc_failure": len(self.total_failures["fc_failure"]),
			},
			"median_pending_duration": self.duration_metrics["median_pending_duration"],
			"median_build_duration": self.duration_metrics["median_build_duration"],
			"median_upload_context_duration": self.context_durations["median_upload_duration"],
			"median_package_context_duration": self.context_durations["median_package_duration"],
			"failure_frequency": dict(self.failure_frequency.most_common()),
			"fc_failure_metrics": self.fc_failure_metrics,
			"build_count_split": self.get_build_count_platform_split(),
		}

	def get_metrics(self):
		"""
		- Get total builds
		- Get total failed builds (user, fc, manually)
		- Get Avg pending and build duration
		- Get Avg context durations (package & upload)
		- Get failure frequency.
		"""
		self.total_builds = self.get_total_builds()
		self.total_failures = self.get_total_failures()
		self.duration_metrics = self.get_build_duration_metrics()
		self.context_durations = self.get_context_durations()
		self.failure_frequency = self.get_error_frequency(
			self.total_failures["user_failure"],
		)
		self.fc_failure_metrics = self.get_fc_failure_metrics()

	def get_error_frequency(
		self,
		user_failures: list[DeployCandidateBuildType],
	) -> Counter:
		"""What type of user addressable failure is most common"""
		return Counter(failure["error_key"] for failure in user_failures)

	def get_context_durations(self) -> ContextDurationType:
		deploy_candidate_build = frappe.qb.DocType("Deploy Candidate Build")
		deploy_candidate_build_step = frappe.qb.DocType("Deploy Candidate Build Step")

		context_durations = (
			frappe.qb.from_(deploy_candidate_build_step)
			.join(deploy_candidate_build)
			.on(deploy_candidate_build_step.parent == deploy_candidate_build.name)
			.select(deploy_candidate_build_step.duration, deploy_candidate_build_step.stage_slug)
			.where(deploy_candidate_build_step.stage_slug.isin(["package", "upload"]))
			.where(deploy_candidate_build_step.step_slug == "context")
			.where(deploy_candidate_build_step.creation[self.from_date : self.end_date])
			.where(deploy_candidate_build.deploy_after_build == 1)
			.run(as_dict=1)
		)

		package_durations = [ctx.duration / 60 for ctx in context_durations if ctx.stage_slug == "package"]
		upload_durations = [ctx.duration / 60 for ctx in context_durations if ctx.stage_slug == "upload"]

		return {
			"median_package_duration": median(package_durations),
			"median_upload_duration": median(upload_durations),
		}

	def get_build_duration_metrics(self) -> DurationType:
		"""Average duration pending / build getting python median"""
		durations = frappe.get_all(
			"Deploy Candidate Build",
			{
				"creation": ["between", (self.from_date, self.end_date)],
				"deploy_after_build": 1,
				"build_duration": ("is", "set"),
				"pending_duration": ("is", "set"),
			},
			["build_duration", "pending_duration"],
		)

		median_pending_duration = median(
			[duration["pending_duration"].total_seconds() / 60 for duration in durations]
		)
		median_build_duration = median(
			[duration["build_duration"].total_seconds() / 60 for duration in durations]
		)

		return {
			"median_build_duration": median_build_duration,
			"median_pending_duration": median_pending_duration,
		}

	def get_total_failures(self) -> FailedBuildType:
		"""User failures, fc failures and manual failures"""
		return {
			"user_failure": self._get_failure(is_user_addressable=True, is_manually_failed=False),
			"fc_failure": self._get_failure(is_user_addressable=False, is_manually_failed=False),
			"fc_manual_failure": self._get_failure(is_user_addressable=False, is_manually_failed=True),
		}

	def _get_failure(
		self, is_user_addressable: bool, is_manually_failed: bool
	) -> list[DeployCandidateBuildType]:
		# Ensure failures are not exaggerated due to conversions
		return frappe.get_all(
			"Deploy Candidate Build",
			{
				"creation": ("between", [self.from_date, self.end_date]),
				"status": "Failure",
				"user_addressable_failure": is_user_addressable,
				"manually_failed": is_manually_failed,
				"deploy_after_build": 1,
			},
			self.metric_fields,
		)

	def _get_build_count(self, filters: dict[str, Any] | None = None):
		# Ensure build creation was not a part of migration using deploy flag.
		if not filters:
			filters = {}

		filters.update(
			{
				"creation": ("between", [self.from_date, self.end_date]),
				"deploy_after_build": 1,
			}
		)

		return frappe.db.count("Deploy Candidate Build", filters=filters)

	def get_build_count_platform_split(self) -> dict[str, int]:
		return {
			"arm64": self._get_build_count({"platform": "arm64"}),
			"x86_64": self._get_build_count({"platform": "x86_64"}),
		}

	def get_total_builds(self) -> int:
		return self._get_build_count()

	@property
	def common_fc_failure_patterns(self):
		return {
			"Node not found": "npm: not found",
			"Permission issue": "permission denied",
			"Timed out": "timeout",
			"Check sum failed": "failed to calculate checksum",
		}

	def get_fc_failure_metrics(self) -> dict[str, dict[str, int]]:
		fc_failures = self._get_failure(is_user_addressable=False, is_manually_failed=False)
		failed_step_frequency = defaultdict(int)
		failure_output_frequency = defaultdict(int)

		for fc_failure in fc_failures:
			step_name, step, output = frappe.db.get_value(
				"Deploy Candidate Build Step",
				{"parent": fc_failure["name"], "status": "Failure"},
				["stage", "step", "output"],
			)

			failure_key = f"{step_name}-{step}"
			failed_step_frequency[failure_key] += 1

			for key, error_key in self.common_fc_failure_patterns.items():
				if output and error_key in output:
					failure_output_frequency[key] += 1

		return {"step_failures": failed_step_frequency, "known_output_failures": failure_output_frequency}


def create_build_metric():
	"""Create build metric triggered from hooks."""
	frappe.new_doc("Build Metric").insert(ignore_permissions=True)
