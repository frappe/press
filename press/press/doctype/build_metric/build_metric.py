# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import typing
from collections import Counter
from dataclasses import dataclass, field

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
	# end: auto-generated types


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
			"avg_pending_duration": self.duration_metrics["avg_pending_duration"],
			"avg_build_duration": self.duration_metrics["avg_build_duration"],
			"avg_upload_context_duration": self.context_durations["avg_upload_duration"],
			"avg_package_context_duration": self.context_durations["avg_package_duration"],
			"failure_frequency": dict(self.failure_frequency),
		}

	def get_metric(self):
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

	def get_error_frequency(
		self,
		user_failures: list[DeployCandidateBuildType],
	) -> Counter:
		"""What type of user addressable failure is most common"""
		return Counter(failure["error_key"] for failure in user_failures)

	def get_context_durations(self) -> ContextDurationType:
		context_durations = frappe.get_all(
			"Deploy Candidate Build Step",
			{
				"stage_slug": ("in", ["package", "upload"]),
				"step_slug": "context",
				"creation": ("between", [frappe.utils.add_to_date(days=-7), frappe.utils.now()]),
			},
			["duration", "stage_slug"],
		)
		package_durations = [ctx.duration for ctx in context_durations if ctx.stage_slug == "package"]
		upload_durations = [ctx.duration for ctx in context_durations if ctx.stage_slug == "upload"]

		return {
			"avg_package_duration": sum(package_durations) / len(package_durations),
			"avg_upload_duration": sum(upload_durations) / len(upload_durations),
		}

	def get_build_duration_metrics(self) -> DurationType:
		"""Average duration pending / build"""
		return frappe.get_value(
			"Deploy Candidate Build",
			filters={"creation": ("between", [self.from_date, self.end_date])},
			fieldname=[
				"AVG(build_duration) as avg_build_duration",
				"AVG(pending_duration) as avg_pending_duration",
			],
			as_dict=True,
		)

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
		return frappe.get_all(
			"Deploy Candidate Build",
			{
				"creation": ("between", [self.from_date, self.end_date]),
				"status": "Failure",
				"user_addressable_failure": is_user_addressable,
				"manually_failed": is_manually_failed,
			},
			self.metric_fields,
		)

	def get_total_builds(self) -> int:
		return frappe.db.count(
			"Deploy Candidate Build",
			{"creation": ("between", [self.from_date, self.end_date])},
		)


def create_build_metric():
	build_metric = GenerateBuildMetric(frappe.utils.add_to_date(days=-7), frappe.utils.now())
	build_metric.get_metric()
	frappe.new_doc("Build Metric", metric_dump=json.dumps(build_metric.dump_metrics(), indent=4)).insert(
		ignore_permissions=True
	)
