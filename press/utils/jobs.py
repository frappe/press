import signal
from collections.abc import Generator
from typing import Any

import frappe
from frappe.core.doctype.rq_job.rq_job import fetch_job_ids
from frappe.utils.background_jobs import get_queues, get_redis_conn
from redis import Redis
from rq.command import send_stop_job_command
from rq.job import Job, JobStatus, NoSuchJobError, get_current_job


def stop_background_job(job: Job):
	try:
		if job.get_status() == JobStatus.STARTED:
			send_stop_job_command(job.connection, job.id)
		elif job.get_status() in [JobStatus.QUEUED, JobStatus.SCHEDULED]:
			job.cancel()
	except Exception:
		return


def get_background_jobs(
	doctype: str,
	name: str,
	status: list[str] | None = None,
	connection: "Redis | None" = None,
) -> Generator[Job, Any, None]:
	"""
	Returns background jobs for a `doc` created using the `run_doc_method`
	Returned jobs are in the QUEUED, SCHEDULED or STARTED state.
	"""
	connection = connection or get_redis_conn()
	status = status or ["queued", "scheduled", "started"]
	for job_id in get_job_ids(status, connection):
		try:
			job = Job.fetch(job_id, connection=connection)
		except NoSuchJobError:
			continue

		if not does_job_belong_to_doc(job, doctype, name):
			continue

		yield job


def get_job_ids(
	status: str | list[str],
	connection: "Redis | None" = None,
) -> Generator[str, Any, None]:
	if isinstance(status, str):
		status = [status]
	connection = connection or get_redis_conn()

	for q in get_queues(connection):
		for s in status:
			try:
				job_ids = fetch_job_ids(q, s)
			# ValueError thrown on macOS
			# Message: signal only works in main thread of the main interpreter
			except ValueError:
				return

			for jid in job_ids:
				yield jid


def does_job_belong_to_doc(job: Job, doctype: str, name: str) -> bool:
	site = job.kwargs.get("site")
	if site and site != frappe.local.site:
		return False

	job_name = job.kwargs.get("job_type") or job.kwargs.get("job_name") or job.kwargs.get("method")
	if job_name != "frappe.utils.background_jobs.run_doc_method":
		return False

	kwargs = job.kwargs.get("kwargs", {})
	if kwargs.get("doctype") != doctype:
		return False

	if kwargs.get("name") != name:
		return False

	return True


def has_job_timeout_exceeded() -> bool:
	# RQ sets up an alarm signal and a signal handler that raises
	# JobTimeoutException after the timeout amount
	# getitimer returns the time left for this timer
	# 0.0 means the timer is expired
	return bool(get_current_job()) and (signal.getitimer(signal.ITIMER_REAL)[0] <= 0)
