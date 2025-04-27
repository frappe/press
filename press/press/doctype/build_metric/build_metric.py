# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import typing
from dataclasses import dataclass, field

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from frappe.utils import DateTimeLikeObject


class BuildMetric(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		metric_dump: DF.JSON | None
	# end: auto-generated types


class DeployCandidateBuildType(typing.TypedDict):
	name: str
	group: str
	status: typing.Literal[
		"Scheduled",
		"Success",
		"Failure",
		"Preparing",
		"Pending",
		"Running",
	]
	creation: DateTimeLikeObject
	error_key: str
	retry_count: int
	build_output: str
	build_error: str
	build_duration: DateTimeLikeObject
	manually_failed: bool
	user_addressable_failure: bool
	pending_duration: DateTimeLikeObject
	user_addressable_failure: bool
	platform: str


class FailedBuildType(typing.TypedDict):
	user_failure: list[DeployCandidateBuildType]
	fc_failure: list[DeployCandidateBuildType]


class DurationType(typing.TypedDict):
	avg_build_duration: float
	avg_pending_duration: float


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

	def get_metric(self):
		self.total_builds = self.get_total_builds()
		self.total_failures = self.get_total_failures()
		self.duration_metrics = self.get_build_duration_metrics()

		from textwrap import dedent

		print(
			dedent(
				f"""
				Total Builds: {self.total_builds} \n
				Total Failures: {len(self.total_failures["user_failure"]), len(self.total_failures["fc_failure"])} \n
				Durations: {self.duration_metrics}
			"""
			)
		)

	def get_build_duration_metrics(self) -> DurationType:
		return frappe.get_all(
			"Deploy Candidate Build",
			filters={"creation": ("between", [self.from_date, self.end_date])},
			fields=[
				"AVG(build_duration) as avg_build_duration",
				"AVG(pending_duration) as avg_pending_duration",
			],
		)

	def get_total_failures(self) -> FailedBuildType:
		return {
			"user_failure": self._get_failure(is_user_addressable=True),
			"fc_failure": self._get_failure(is_user_addressable=False),
		}

	def _get_failure(self, is_user_addressable: bool) -> list[DeployCandidateBuildType]:
		return frappe.get_all(
			"Deploy Candidate Build",
			{
				"creation": ("between", [self.from_date, self.end_date]),
				"status": "Failure",
				"user_addressable_failure": is_user_addressable,
			},
			# self.metric_fields,
		)

	def get_total_builds(self) -> DeployCandidateBuildType:
		return frappe.db.count(
			"Deploy Candidate Build",
			{"creation": ("between", [self.from_date, self.end_date])},
			self.metric_fields,
		)


def create_build_metric():
	"""Create build metric"""
	build_metric = GenerateBuildMetric(
		frappe.utils.add_to_date(days=-7),
		frappe.utils.add_to_date(days=1),
	)
	build_metric.get_metric()
