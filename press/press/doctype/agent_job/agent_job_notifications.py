# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing
from typing import Protocol, TypedDict

import frappe

"""
Used to create notifications if the Agent Job error is something that can
be handled by the user.

Based on https://github.com/frappe/press/pull/1544

To handle an error:
1. Create a doc page that helps the user get out of it under: frappecloud.com/docs/common-issues
2. Check if the error is the known/expected one in `get_details`.
3. Update the details object with the correct values.
"""


class Details(TypedDict):
	title: str | None
	message: str
	traceback: str | None
	is_actionable: bool
	assistance_url: str | None


# These strings are checked against the traceback or output of the job
MatchStrings = str | list[str]

if typing.TYPE_CHECKING:
	# TYPE_CHECKING guard for code below cause DeployCandidate
	# might cause circular import.
	class UserAddressableHandler(Protocol):
		def __call__(
			self,
			details: "Details",
			job: "AgentJob",
		) -> bool:  # Return True if is_actionable
			...

	UserAddressableHandlerTuple = tuple[
		MatchStrings,
		UserAddressableHandler,
	]


DOC_URLS = {
	"oom-issues": "https://frappecloud.com/docs/common-issues/oom-issues",
}


def handlers() -> "list[UserAddressableHandlerTuple]":
	"""
	Before adding anything here, view the type:
	`UserAddressableHandlerTuple`

	The first value of the tuple is `MatchStrings` which
	a list of strings (or a single string) which if they
	are present in the `traceback` or the `output`
	then then second value i.e. `UserAddressableHandler`
	is called.

	`UserAddressableHandler` is used to update the details
	used to create the Press Notification

	`UserAddressableHandler` can return False if it isn't
	user addressable, in this case the remaining handler
	tuple will be checked.

	Due to this order of the tuples matter.
	"""
	return [
		("returned non-zero exit status 137", update_with_oom_error),
		("returned non-zero exit status 143", update_with_oom_error),
	]


def create_job_failed_notification(
	job: "AgentJob",
	team: str,
	notification_type: str = "Agent Job Failure",
	message: str = "",
) -> bool:
	"""
	Used to create press notifications on Job failures. If the notification
	is actionable then it will be displayed on the dashboard.

	Returns True if job failure is_actionable
	"""

	details = get_details(job, message)
	doc_dict = {
		"doctype": "Press Notification",
		"team": team,
		"type": notification_type,
		"document_type": job.doctype,
		"document_name": job.name,
		"class": "Error",
		**details,
	}
	doc = frappe.get_doc(doc_dict)
	doc.insert()
	frappe.db.commit()

	frappe.publish_realtime("press_notification", doctype="Press Notification", message={"team": team})

	return details["is_actionable"]


def get_details(job: "AgentJob", message: str) -> "Details":
	tb = job.traceback or ""
	output = job.output or ""
	default_title = get_default_title(job)
	default_message = get_default_message(job)

	details: "Details" = dict(
		title=default_title,
		message=message or default_message,
		traceback=tb,
		is_actionable=False,
		assistance_url=None,
	)

	for strs, handler in handlers():
		if isinstance(strs, str):
			strs = [strs]

		if not (is_match := all(s in tb for s in strs)):
			is_match = all(s in output for s in strs)

		if not is_match:
			continue

		if handler(details, job):
			details["is_actionable"] = True
			break
		details["title"] = default_title
		details["message"] = message or default_message
		details["traceback"] = tb
		details["is_actionable"] = False
		details["assistance_url"] = None

	return details


def update_with_oom_error(
	details: "Details",
	job: "AgentJob",
):
	details["title"] = "Server out of memory error"

	job_type = ""
	if job.job_type == "Update Site Migrate":
		job_type = "Site Migrate"
	elif job.job_type == "Update Site Pull":
		job_type = "Site Update"

	details[
		"message"
	] = f"""<p>The server ran out of memory while {job_type} job was running and was killed by the system.</p>
    <p>It is recommended to increase the memory available for the server <a class="underline" href="/dashboard/servers/{job.server}">{job.server}</a>.</p>
	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["assistance_url"] = DOC_URLS["oom-issues"]

	# user addressable if the server is a dedicated server
	if not frappe.db.get_value(job.server_type, job.server, "public"):
		return True
	return False


def get_default_title(job: "AgentJob") -> str:
	return "Job Failed"


def get_default_message(job: "AgentJob") -> str:
	if job.site:
		return f"<b>{job.job_type}</b> job failed on site <b>{job.site}</b>."

	return f"<b>{job.job_type}</b> job failed on server <b>{job.server}</b>."


def send_job_failure_notification(job: "Agent Job"):
	from press.press.doctype.site_migration.site_migration import (
		get_ongoing_migration,
		job_matches_site_migration,
	)

	# site migration has its own notification handling
	site_migration = get_ongoing_migration(job.site)
	if site_migration and job_matches_site_migration(job, site_migration):
		return

	notification_type = "Agent Job Failure"
	message = ""
	team = None

	if job.job_type == "Update Site Migrate":
		notification_type = "Site Migrate"
		message = f"Site <b>{job.site}</b> failed to migrate"
	elif job.job_type == "Update Site Pull":
		notification_type = "Site Update"
		message = f"Site <b>{job.site}</b> failed to update"
	elif job.job_type.startswith("Recover Failed"):
		notification_type = "Site Recovery"
		message = f"Site <b>{job.site}</b> failed to recover after a failed update/migration"

	if site_team := frappe.get_value("Site", job.site, "team"):
		team = site_team
	else:
		if job.server_type not in ["Server", "Database Server"]:
			return

		server = frappe.get_value(job.server_type, job.server, ["team", "public"])
		if server["public"]:
			return
		team = server["team"]

	create_job_failed_notification(job, team, notification_type, message)
