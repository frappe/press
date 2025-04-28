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
	avg_build_duration: float
	avg_pending_duration: float


class ContextDurationType(typing.TypedDict):
	avg_package_duration: float
	avg_upload_duration: float
