# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import typing
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import median, quantiles
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
		build_metric_dump = build_metric.dump_metrics()
		deploy_metric_dump = deploy_metrics(self.start_from, self.to)
		self.metric_dump = json.dumps(
			{"build_metric": build_metric_dump, "deploy_metric": deploy_metric_dump}, indent=4
		)
		self.save()

	@frappe.whitelist()
	def get_metrics(self):
		"""Retrigger metrics"""
		frappe.enqueue(self._get_metrics)


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
			# Deployment Info
			"total_deployments": self.total_deployment_info[
				"total_deployments"
			],  # Should be same as total builds?
			"successful_deployments": self.total_deployment_info["successful_deployments"],
			"failed_deployments": self.total_deployment_info["failed_deployments"],
			# Pending durations
			"median_pending_duration": self.build_duration_metrics["median_pending_duration"],
			"p90_pending_duration": self.build_duration_metrics["p90_pending_duration"],
			"p99_pending_duration": self.build_duration_metrics["p99_pending_duration"],
			# Build durations
			"median_build_duration": self.build_duration_metrics["median_build_duration"],
			"p90_build_duration": self.build_duration_metrics["p90_build_duration"],
			"p99_build_duration": self.build_duration_metrics["p99_build_duration"],
			# Context durations (upload & package)
			"median_upload_context_duration": self.context_durations["median_upload_duration"],
			"p90_upload_context_duration": self.context_durations["p90_upload_duration"],
			"p99_upload_context_duration": self.context_durations["p99_upload_duration"],
			"median_package_context_duration": self.context_durations["median_package_duration"],
			"p90_package_context_duration": self.context_durations["p90_package_duration"],
			"p99_package_context_duration": self.context_durations["p99_package_duration"],
			"median_deploy_duration": self.deploy_duration_metrics,
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
		self.total_deployment_info = self.get_total_deployment_info()
		self.total_builds = self.get_total_builds()
		self.total_failures = self.get_total_failures()
		self.build_duration_metrics = self.get_build_duration_metrics()
		self.deploy_duration_metrics = self.get_deploy_duration_metrics()
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

	@staticmethod
	def p(values, percentile):
		if not values:
			return None
		return quantiles(values, n=100)[percentile - 1]

	def get_total_deployment_info(self) -> dict[str, int]:
		deploy_candidate_build = frappe.qb.DocType("Deploy Candidate Build")
		agent_job = frappe.qb.DocType("Agent Job")
		bench = frappe.qb.DocType("Bench")

		query = (
			frappe.qb.from_(deploy_candidate_build)
			.join(bench)
			.on(deploy_candidate_build.name == bench.build)
			.join(agent_job)
			.on(agent_job.bench == bench.name)
			.select(
				deploy_candidate_build.name,
				bench.name.as_("bench_name"),
				agent_job.name.as_("agent_job_name"),
				agent_job.status.as_("agent_job_status"),
			)
			.where(agent_job.job_type == "New Bench")
			.where(deploy_candidate_build.status == "Success")
			.where(deploy_candidate_build.creation[self.from_date : self.end_date])
			.where(deploy_candidate_build.deploy_after_build == 1)
		)

		results = query.run(as_dict=1)
		successful_deployments = sum(1 for r in results if r.agent_job_status == "Success")
		failed_deployments = sum(1 for r in results if r.agent_job_status == "Failure")

		return {
			"total_deployments": len(results),
			"successful_deployments": successful_deployments,
			"failed_deployments": failed_deployments,
		}

	def get_context_durations(self) -> ContextDurationType:
		"""Compute median, p90, and p99 for package/upload durations."""
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
			# Package
			"median_package_duration": median(package_durations) if package_durations else None,
			"p90_package_duration": self.p(package_durations, 90),
			"p99_package_duration": self.p(package_durations, 99),
			# Upload
			"median_upload_duration": median(upload_durations) if upload_durations else None,
			"p90_upload_duration": self.p(upload_durations, 90),
			"p99_upload_duration": self.p(upload_durations, 99),
		}

	def get_build_duration_metrics(self) -> DurationType:
		"""Compute median, p90, and p99 for pending/build durations."""
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

		pending_minutes = [d["pending_duration"].total_seconds() / 60 for d in durations]
		build_minutes = [d["build_duration"].total_seconds() / 60 for d in durations]

		return {
			# pending
			"median_pending_duration": median(pending_minutes) if pending_minutes else None,
			"p90_pending_duration": self.p(pending_minutes, 90),
			"p99_pending_duration": self.p(pending_minutes, 99),
			# build
			"median_build_duration": median(build_minutes) if build_minutes else None,
			"p90_build_duration": self.p(build_minutes, 90),
			"p99_build_duration": self.p(build_minutes, 99),
		}

	def get_deploy_duration_metrics(self) -> float:
		deploy_durations = frappe.db.get_all(
			"Agent Job",
			{
				"job_type": "New Bench",
				"creation": ("between", [self.from_date, self.end_date]),
				"status": "Success",
			},
			pluck="duration",
		)
		return median([deploy_duration.total_seconds() / 60 for deploy_duration in deploy_durations])

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
		failed_step_frequency: defaultdict[str, int] = defaultdict(int)
		failure_output_frequency: defaultdict[str, int] = defaultdict(int)

		for fc_failure in fc_failures:
			failed_build_step = frappe.db.get_value(
				"Deploy Candidate Build Step",
				{"parent": fc_failure["name"], "status": "Failure"},
				["stage", "step", "output"],
			)
			if not failed_build_step:
				continue

			step_name, step, output = failed_build_step

			failure_key = f"{step_name}-{step}"
			failed_step_frequency[failure_key] += 1

			for key, error_key in self.common_fc_failure_patterns.items():
				if output and error_key in output:
					failure_output_frequency[key] += 1

		return {"step_failures": failed_step_frequency, "known_output_failures": failure_output_frequency}


def deploy_metrics(start_from: DateTimeLikeObject, to: DateTimeLikeObject) -> dict[str, int]:
	"""Get deploy failure metrics"""

	no_space = []
	port_offset = []
	missing_docker_layer = []
	missing_docker_image = []
	registry_timeout = []
	missing_files = []
	others = []

	failed_new_bench_jobs = frappe.get_all(
		"Agent Job",
		{
			"status": "Failure",
			"job_type": "New Bench",
			"creation": ("between", [start_from, to]),
		},
	)
	all_new_bench_jobs = frappe.get_all(
		"Agent Job",
		{
			"job_type": "New Bench",
			"creation": ("between", [start_from, to]),
		},
	)

	for agent_job in failed_new_bench_jobs:
		output = frappe.db.get_value("Agent Job", agent_job, ["output"])
		output = output.casefold() if output else ""

		if "no space" in output:
			no_space.append(agent_job)
		elif "port is already allocated" in output:
			port_offset.append(agent_job)
		elif "docker: unknown blob" in output:
			missing_docker_layer.append(agent_job)
		elif "manifest unknown" in output:
			missing_docker_image.append(agent_job)
		elif "tls handshake timeout" in output:
			registry_timeout.append(agent_job)
		elif "no such file or directory" in output:
			missing_files.append(agent_job)
		else:
			others.append(agent_job)

	return {
		"total_deploys": len(all_new_bench_jobs),
		"failed_deploys": len(failed_new_bench_jobs),
		"no_space": len(no_space),
		"port_offset": len(port_offset),
		"missing_docker_layer": len(missing_docker_layer),
		"missing_docker_image": len(missing_docker_image),
		"registry_timeout": len(registry_timeout),
		"missing_files": len(missing_files),
		"other": len(others),
	}


def create_build_metric():
	"""Create build metric triggered from hooks."""
	frappe.new_doc("Build Metric").insert(ignore_permissions=True)
