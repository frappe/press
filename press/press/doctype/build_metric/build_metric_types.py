from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
	from frappe.utils import DateTimeLikeObject


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
	fc_manually_failed: list[DeployCandidateBuildType]


class DurationType(typing.TypedDict):
	median_build_duration: float
	median_pending_duration: float


class ContextDurationType(typing.TypedDict):
	median_package_duration: float
	median_upload_duration: float


class TotalFailuresDict(typing.TypedDict):
	user_failure: int
	fc_manual_failure: int
	fc_failure: int


class MetricsType(typing.TypedDict):
	total_builds: int
	total_failures: TotalFailuresDict
	median_pending_duration: float
	median_build_duration: float
	median_upload_context_duration: float
	median_package_context_duration: float
	failure_frequency: dict[str, int]
	build_count_split: dict[str, int]
	fc_failure_metrics: dict[str, dict[str, int]]
