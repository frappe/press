# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing
from enum import Enum, auto
from typing import Protocol, TypedDict

import frappe

"""
Used to create notifications if the Agent Job error is something that can
be handled by the user.

Based on https://github.com/frappe/press/pull/1544

To handle an error:
1. Create a doc page that helps the user get out of it under: docs.frappe.io/cloud/common-issues
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

	from press.press.doctype.agent_job.agent_job import AgentJob

	class UserAddressableHandler(Protocol):
		def __call__(
			self,
			details: Details,
			job: AgentJob,
		) -> bool:  # Return True if is_actionable
			...

	UserAddressableHandlerTuple = tuple[
		MatchStrings,
		UserAddressableHandler,
	]


class JobErr(Enum):
	OOM = auto()
	ROW_SIZE_TOO_LARGE = auto()
	DATA_TRUNCATED_FOR_COLUMN = auto()
	BROKEN_PIPE_ERR = auto()
	CANT_CONNECT_TO_MYSQL = auto()
	LOST_CONN_TO_MYSQL = auto()
	GZIP_TAR_ERR = auto()
	UNKNOWN_COMMAND_HYPHEN = auto()
	RQ_JOBS_IN_QUEUE = auto()


DOC_URLS = {
	JobErr.OOM: "https://docs.frappe.io/cloud/common-issues/oom-issues",
	JobErr.ROW_SIZE_TOO_LARGE: "https://docs.frappe.io/cloud/faq/site#row-size-too-large-error-on-migrate",
	JobErr.DATA_TRUNCATED_FOR_COLUMN: "https://docs.frappe.io/cloud/faq/site#data-truncated-for-column",
	JobErr.BROKEN_PIPE_ERR: None,
	JobErr.CANT_CONNECT_TO_MYSQL: "https://docs.frappe.io/cloud/cant-connect-to-mysql-server",
	JobErr.LOST_CONN_TO_MYSQL: "https://docs.frappe.io/cloud/site/common-issues/lost-connection-to-mysql-server",
	JobErr.GZIP_TAR_ERR: "https://docs.frappe.io/cloud/sites/migrate-an-existing-site#tar-gzip-command-fails-with-unexpected-eof",
	JobErr.UNKNOWN_COMMAND_HYPHEN: "https://docs.frappe.io/cloud/unknown-command-",
	JobErr.RQ_JOBS_IN_QUEUE: "https://docs.frappe.io/cloud/faq/site#how-do-i-deactivate-my-site-",
}


def handlers() -> list[UserAddressableHandlerTuple]:
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
		("returned non-zero exit status 137", update_with_oom_err),
		("returned non-zero exit status 143", update_with_oom_err),
		("b'Terminated\\n'", update_with_oom_err),
		("Row size too large", update_with_row_size_too_large_err),
		("Data truncated for column", update_with_data_truncated_for_column_err),
		("BrokenPipeError", update_with_broken_pipe_err),
		("ERROR 2002 (HY000)", update_with_cant_connect_to_mysql_err),
		("Lost connection to server during query", update_with_lost_conn_to_mysql_err),
		("gzip: stdin: unexpected end of file", update_with_gzip_tar_err),
		("tar: Unexpected EOF in archive", update_with_gzip_tar_err),
		("Unknown command '\\-'.", update_with_unknown_command_hyphen_err),
		('redis_host, redis_port = redis_url.split(":")', update_with_redis_unpack_error),
		("Site might have lot of jobs in queue.", update_with_rq_jobs_in_queue_err),
	]


def create_job_failed_notification(
	job: AgentJob,
	team: str,
	notification_type: str = "Agent Job Failure",
	title: str = "",
	message: str = "",
) -> bool:
	"""
	Used to create press notifications on Job failures. If the notification
	is actionable then it will be displayed on the dashboard.

	Returns True if job failure is_actionable
	"""

	details = get_details(job, title, message)
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


def get_details(job: AgentJob, title: str, message: str) -> Details:
	tb = job.traceback or ""
	output = job.output or ""
	title = title or get_default_title(job)
	message = message or get_default_message(job)

	details = Details(
		title=title,
		message=message,
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
		details["title"] = title
		details["message"] = message
		details["traceback"] = tb
		details["is_actionable"] = False
		details["assistance_url"] = None

	return details


def update_with_oom_err(
	details: Details,
	job: AgentJob,
):
	details["title"] = "Server out of memory error"

	details[
		"message"
	] = f"""<p>The server ran out of memory while {job.job_type} job was running and was killed by the system.</p>
	<p>It is recommended to increase the memory available for the server <a class="underline" href="/dashboard/servers/{job.server}">{job.server}</a>.</p>
	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.OOM]

	# user addressable if the server is a dedicated server
	if not frappe.db.get_value(job.server_type, job.server, "public"):
		return True
	return False


def update_with_row_size_too_large_err(details: Details, job: AgentJob):
	details["title"] = "Row size too large error"

	details[
		"message"
	] = f"""<p>The server encountered a row size too large error while migrating the site <b>{job.site}</b>.</p>
	<p>This tends to happen on doctypes with many custom fields</p>
	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.ROW_SIZE_TOO_LARGE]

	return True


def update_with_data_truncated_for_column_err(details: Details, job: AgentJob):
	details["title"] = "Data truncated for column error"

	details[
		"message"
	] = f"""<p>The server encountered a data truncated for column error while migrating the site <b>{job.site}</b>.</p>
	<p>This tends to happen when the datatype of a field changes, but there is existing data in the doctype that don't fit to the new datatype</p>
	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.DATA_TRUNCATED_FOR_COLUMN]

	return True


def update_with_redis_unpack_error(details: Details, job: AgentJob):
	"""Add this message for every job that faces redis unpack issue"""
	details["title"] = "Framework version bump required"

	details["message"] = (
		"<p>This job failed because the current framework version is outdated.</p>"
		"<p>To maintain security and compatibility, please update your framework:</p>"
		"<p><strong>v14 benches:</strong> upgrade to <strong>v14.99.4</strong> or newer.<br>"
		"<strong>v13 benches:</strong> upgrade to <strong>v13.58.22</strong> or newer.</p>"
	)

	return True


def update_with_broken_pipe_err(details: Details, job: AgentJob):
	if not job.failed_because_of_agent_update:
		return False

	details["title"] = "Job failed due to maintenance activity on the server"

	details[
		"message"
	] = f"""<p>The ongoing job coincided with a maintenance activity on the server <b>{job.server}</b> and hence failed.</p>
	<p>Please try again in a few minutes.</p>
	"""

	return True


def update_with_cant_connect_to_mysql_err(details: Details, job: AgentJob):
	details["title"] = "Can't connect to MySQL server"

	suggestion = "To rectify this issue, please follow the steps mentioned in <i>Help</i>."
	if job.on_public_server:
		suggestion = "Please raise a support ticket if the issue persists."

	details[
		"message"
	] = f"""<p>The server couldn't connect to MySQL server during the job. This likely happened as the mysql server restarted as it didn't have sufficient memory for the operation. Please retry.</p>
	<p>{suggestion}</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.CANT_CONNECT_TO_MYSQL]

	return True


def update_with_lost_conn_to_mysql_err(details: Details, job: AgentJob):
	details["title"] = "Lost connection to MySQL server during query"

	suggestion = (
		"If the issue persists, please follow the steps mentioned in <i>Help</i> to rectify this issue"
	)
	if job.on_public_server:
		suggestion = "Please raise a support ticket if the issue persists."

	details[
		"message"
	] = f"""<p>The server lost connection to MySQL server during the job. This likely happened as the mysql server restarted as it didn't have sufficient memory for the operation. Please retry.</p>
	<p>{suggestion}</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.LOST_CONN_TO_MYSQL]

	return True


def update_with_gzip_tar_err(details: Details, job: AgentJob):
	details["title"] = "Corrupt backup file"

	details["message"] = f"""<p>An error occurred when extracting the backup to {job.site}.</p>
	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.GZIP_TAR_ERR]

	return True


def update_with_unknown_command_hyphen_err(details: Details, job: AgentJob):
	details["title"] = "Incompatible site backup"

	details["message"] = f"""<p>An error occurred when extracting the backup to {job.site}.</p>
	<p>This happens when the backup is taken from a later version of MariaDB and restored on a older version.</p>
	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.UNKNOWN_COMMAND_HYPHEN]

	return True


def update_with_rq_jobs_in_queue_err(details: Details, job: AgentJob):
	if job.job_type not in ["Update Site Pull", "Update Site Migrate"]:
		return False

	details["title"] = "High number of queued jobs"

	details["message"] = """<p>The job could not be processed because there are too many jobs getting queued.
	If this continues to happen upon retry, please <b>deactivate</b> your site, wait for 5 minutes and try again. You may activate it again once the update is finished</p>
	<p>Click <i>help</i> for instructions on how to deactivate your site.</p>


	<p><b>NOTE</b>: This will cause downtime for that duration</p>
	"""

	details["assistance_url"] = DOC_URLS[JobErr.RQ_JOBS_IN_QUEUE]

	return True


def get_default_title(job: AgentJob) -> str:
	if job.job_type == "Update Site Migrate":
		return "Site Migrate"
	if job.job_type == "Update Site Pull":
		return "Site Update"
	if job.job_type.startswith("Recover Failed"):
		return "Site Recovery"
	return "Job Failure"


def get_default_message(job: AgentJob) -> str:
	if job.job_type == "Update Site Migrate":
		return f"Site <b>{job.site}</b> failed to migrate"
	if job.job_type == "Update Site Pull":
		return f"Site <b>{job.site}</b> failed to update"
	if job.job_type.startswith("Recover Failed"):
		return f"Site <b>{job.site}</b> failed to recover after a failed update/migration"
	if job.site:
		return f"<b>{job.job_type}</b> job failed on site <b>{job.site}</b>."
	return f"<b>{job.job_type}</b> job failed on server <b>{job.server}</b>."


def send_job_failure_notification(job: AgentJob):
	from press.press.doctype.site_migration.site_migration import (
		get_ongoing_migration,
		job_matches_site_migration,
	)

	# site migration has its own notification handling
	site_migration = get_ongoing_migration(job.site) if job.site else None
	if site_migration and job_matches_site_migration(job, site_migration):
		return

	notification_type = get_notification_type(job)
	team = None

	if job.reference_doctype == "Site Database User":
		return

	if job.site:
		team = frappe.get_value("Site", job.site, "team")
	else:
		if job.server_type not in ["Server", "Database Server"]:
			return

		server = frappe.db.get_value(job.server_type, job.server, ["team", "public"], as_dict=True)
		if server["public"]:
			return

		team = server["team"]

	if not team:
		return

	create_job_failed_notification(job, team, notification_type)


def get_notification_type(job: AgentJob) -> str:
	if job.job_type == "Update Site Migrate":
		return "Site Migrate"
	if job.job_type == "Update Site Pull":
		return "Site Update"
	if job.job_type.startswith("Recover Failed"):
		return "Site Recovery"
	return "Agent Job Failure"
