# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
import os
import random
import traceback
from typing import TYPE_CHECKING

import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.monitor import add_data_to_monitor
from frappe.utils import (
	add_days,
	cint,
	convert_utc_to_system_timezone,
	cstr,
	get_datetime,
	now_datetime,
)

from press.access.support_access import has_support_access
from press.agent import Agent, AgentCallbackException, AgentRequestSkippedException
from press.api.client import is_owned_by_team
from press.press.doctype.agent_job_type.agent_job_type import (
	get_retryable_job_types_and_max_retry_count,
)
from press.press.doctype.site_database_user.site_database_user import SiteDatabaseUser
from press.press.doctype.site_migration.site_migration import (
	get_ongoing_migration,
	process_site_migration_job_update,
)
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.utils import log_error, timer

AGENT_LOG_KEY = "agent-jobs"
AGENT_JOB_TIMEOUT_HOURS = 4

BYPASS_AGENT_JOB_HALT = ["Change Bench Directory", "Remove Redis Localhost Bind"]


class AgentJob(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link | None
		callback_failure_count: DF.Int
		code_server: DF.Link | None
		data: DF.Code | None
		duration: DF.Time | None
		end: DF.Datetime | None
		host: DF.Link | None
		job_id: DF.Int
		job_type: DF.Link
		next_retry_at: DF.Datetime | None
		output: DF.Code | None
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		request_data: DF.Code
		request_files: DF.Code | None
		request_method: DF.Literal["GET", "POST", "DELETE"]
		request_path: DF.Data
		retry_count: DF.Int
		server: DF.DynamicLink
		server_type: DF.Link
		site: DF.Link | None
		start: DF.Datetime | None
		status: DF.Literal["Undelivered", "Pending", "Running", "Success", "Failure", "Delivery Failure"]
		traceback: DF.Code | None
		upstream: DF.Link | None
	# end: auto-generated types

	dashboard_fields = (
		"name",
		"job_type",
		"creation",
		"status",
		"start",
		"end",
		"duration",
		"bench",
		"site",
		"server",
		"job_id",
		"output",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		site = cstr(filters.get("site", ""))
		group = cstr(filters.get("group", ""))
		server = cstr(filters.get("server", ""))
		bench = cstr(filters.get("bench", ""))

		if not (site or group or server or bench):
			frappe.throw("Not permitted", frappe.PermissionError)

		if site and not has_support_access("Site", site):
			is_owned_by_team("Site", site, raise_exception=True)

		if group:
			if not has_support_access("Release Group", group):
				is_owned_by_team("Release Group", group, raise_exception=True)

			AgentJob = frappe.qb.DocType("Agent Job")
			Bench = frappe.qb.DocType("Bench")
			benches = frappe.qb.from_(Bench).select(Bench.name).where(Bench.group == filters.group)
			query = query.where(AgentJob.bench.isin(benches))

		if server:
			is_owned_by_team("Server", server, raise_exception=True)

		results = query.run(as_dict=1)
		update_query_result_status_timestamps(results)
		return results

	def get_doc(self, doc):
		if doc.status == "Undelivered" and not doc.output:
			doc.status = "Pending"

		doc["steps"] = frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": self.name},
			fields=[
				"name",
				"step_name",
				"status",
				"start",
				"end",
				"duration",
				"output",
			],
			order_by="creation",
		)
		# agent job start and end are in utc
		if doc.start:
			doc.start = convert_utc_to_system_timezone(doc.start).replace(tzinfo=None)
		if doc.end:
			doc.end = convert_utc_to_system_timezone(doc.end).replace(tzinfo=None)

		for step in doc["steps"]:
			if step.status == "Running":
				step.output = frappe.cache.hget("agent_job_step_output", step.name)

		return doc

	def after_insert(self):
		self.create_agent_job_steps()
		self.log_creation()
		self.enqueue_http_request()

	def enqueue_http_request(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"create_http_request",
			timeout=600,
			queue="short",
			enqueue_after_commit=True,
		)

	def create_http_request(self):
		try:
			agent = Agent(self.server, server_type=self.server_type)
			if agent.should_skip_requests() and self.job_type not in BYPASS_AGENT_JOB_HALT:
				self.retry_count = 0
				self.set_status_and_next_retry_at()
				return

			data = json.loads(self.request_data)
			files = json.loads(self.request_files)

			self.job_id = agent.request(self.request_method, self.request_path, data, files, agent_job=self)[
				"job"
			]

			self.status = "Pending"
			self.save()
		except AgentRequestSkippedException:
			self.retry_count = 0
			self.set_status_and_next_retry_at()

		except Exception:
			if 400 <= cint(self.flags.get("status_code", 0)) <= 499:
				self.status = "Failure"
				self.save()
				frappe.db.commit()

				process_job_updates(self.name)

			else:
				self.set_status_and_next_retry_at()

	def log_creation(self):
		try:
			if hasattr(frappe.local, "monitor"):
				monitor = frappe.local.monitor.data
			else:
				monitor = None

			data = {
				"monitor": monitor,
				"timestamp": frappe.utils.now(),
				"job": self.as_dict(),
			}
			serialized = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
			frappe.cache().rpush(AGENT_LOG_KEY, serialized)
		except Exception:
			traceback.print_exc()

	def set_status_and_next_retry_at(self):
		try:
			next_retry_at = get_next_retry_at(self.retry_count)
			self._update_retry_fields(next_retry_at)

		except frappe.TimestampMismatchError:
			self.reload()
			self._update_retry_fields(next_retry_at)

		except Exception:
			log_error("Agent Job Set Next Retry Timing", job=self)

	def _update_retry_fields(self, next_retry_at):
		if not self.retry_count:
			self.retry_count = 1

		self.status = "Undelivered"
		self.next_retry_at = next_retry_at

		self.save()
		frappe.db.commit()

	def create_agent_job_steps(self):
		job_type = frappe.get_doc("Agent Job Type", self.job_type)
		for step in job_type.steps:
			doc = frappe.get_doc(
				{
					"doctype": "Agent Job Step",
					"agent_job": self.name,
					"status": "Pending",
					"step_name": step.step_name,
					"duration": "00:00:00",
				}
			)
			doc.insert()

	@frappe.whitelist()
	def retry(self):
		return frappe.get_doc(
			{
				"doctype": "Agent Job",
				"status": "Undelivered",
				"job_type": self.job_type,
				"server_type": self.server_type,
				"server": self.server,
				"bench": self.bench,
				"site": self.site,
				"upstream": self.upstream,
				"host": self.host,
				"request_path": self.request_path,
				"request_data": self.request_data,
				"request_files": self.request_files,
				"request_method": self.request_method,
			}
		).insert()

	@frappe.whitelist()
	def retry_in_place(self):
		self.enqueue_http_request()
		frappe.db.commit()

	@frappe.whitelist()
	def get_status(self):
		agent = Agent(self.server, server_type=self.server_type)

		if not self.job_id:
			job = agent.get_jobs_id(self.name)
			if job and len(job) > 0:
				self.db_set("job_id", job[0]["id"])
		if self.job_id:
			polled_job = agent.get_job_status(self.job_id)
			update_job(self.name, polled_job)
			update_steps(self.name, polled_job)

	@frappe.whitelist()
	def retry_skip_failing_patches(self):
		# Add the skip flag and update request data
		updated_request_data = json.loads(self.request_data) if self.request_data else {}
		updated_request_data["skip_failing_patches"] = True
		self.request_data = json.dumps(updated_request_data, indent=4, sort_keys=True)

		return self.retry()

	@frappe.whitelist()
	def succeed_and_process_job_updates(self):
		self.status = "Success"
		self.save()
		self.process_job_updates()

	@frappe.whitelist()
	def fail_and_process_job_updates(self):
		self.status = "Failure"
		self.save()
		self.process_job_updates()

	@frappe.whitelist()
	def process_job_updates(self):
		process_job_updates(self.name)

	@frappe.whitelist()
	def cancel_job(self):
		agent = Agent(self.server, server_type=self.server_type)
		agent.cancel_job(self.job_id)

	def on_trash(self):
		steps = frappe.get_all("Agent Job Step", filters={"agent_job": self.name})
		for step in steps:
			frappe.delete_doc("Agent Job Step", step.name)

		frappe.db.delete(
			"Press Notification",
			{"document_type": self.doctype, "document_name": self.name},
		)

	def get_step_status(self, step_name: str):
		if statuses := frappe.get_all(
			"Agent Job Step",
			fields=["status"],
			filters={"agent_job": self.name, "step_name": step_name},
			pluck="status",
			limit=1,
		):
			return statuses[0]

		return None

	@property
	def failed_because_of_agent_update(self) -> bool:
		if "BrokenPipeError" in str(self.traceback) and frappe.db.exists(
			"Ansible Play",
			{
				"play": "Update Agent",
				"server": self.server,
				"creation": (">", frappe.utils.add_to_date(None, minutes=-15)),
			},
		):
			return True
		return False

	@property
	def failed_because_of_incident(self) -> bool:
		if self.server and frappe.db.exists(
			"Incident",
			{
				"server": self.server,
				"status": ("in", ["Auto-Resolved", "Resolved", "Press-Resolved"]),
				"creation": (
					"between",
					[
						frappe.utils.add_to_date(self.creation, minutes=-15),
						self.creation,
					],
				),  # incident didn't happen because of job
			},
		):
			return True
		return False

	@property
	def on_public_server(self):
		return bool(frappe.db.get_value(self.server_type, self.server, "public"))


def job_detail(job):
	job = frappe.get_doc("Agent Job", job)
	steps = []
	current = {}
	for index, job_step in enumerate(
		frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": job.name},
			fields=[
				"name",
				"step_name",
				"status",
				"start",
				"end",
				"duration",
				"output",
			],
			order_by="creation",
		)
	):
		step = {"name": job_step.step_name, "index": index, **job_step}
		if job_step.status == "Running":
			step["output"] = frappe.cache.hget("agent_job_step_output", job_step.name)
			current = step
		steps.append(step)

	if job.status == "Pending":
		current = {"name": job.job_type, "status": "Waiting", "index": -1}
	elif job.status in ("Success", "Failure"):
		current = {"name": job.job_type, "status": job.status, "index": len(steps)}

	current["total"] = len(steps)

	return {
		"id": job.name,
		"name": job.job_type,
		"server": job.server,
		"bench": job.bench,
		"site": job.site,
		"status": job.status,
		"steps": steps,
		"current": current,
	}


def publish_update(job):
	message = job_detail(job)
	frappe.publish_realtime(event="agent_job_update", doctype="Agent Job", docname=job, message=message)

	# publish event for agent job list to update in dashboard
	# we are doing this since process agent job doesn't emit list_update for job due to set_value
	frappe.publish_realtime(event="list_update", message={"doctype": "Agent Job", "name": job})

	# publish event for site to show job running on dashboard and update site
	# we are doing this since process agent job doesn't emit doc_update for site due to set_value
	if message["site"]:
		frappe.publish_realtime(
			event="doc_update",
			doctype="Site",
			docname=message["site"],
			message={
				"doctype": "Site",
				"name": message["site"],
				"status": message["status"],
				"id": message["id"],
				"site": message["site"],
			},
		)


@timer
def poll_random_jobs(agent, pending_ids):
	random_pending_ids = random.sample(pending_ids, k=min(100, len(pending_ids)))
	return agent.get_jobs_status(random_pending_ids)


@timer
def handle_polled_jobs(polled_jobs, pending_jobs):
	for polled_job in polled_jobs:
		if not polled_job:
			continue
		handle_polled_job(pending_jobs=pending_jobs, polled_job=polled_job)


def add_timer_data_to_monitor(server):
	if not hasattr(frappe.local, "timers"):
		frappe.local.timers = {}

	add_data_to_monitor(server=server, timing=frappe.local.timers)


def poll_pending_jobs_server(server):
	if frappe.db.get_value(server.server_type, server.server, "status") != "Active":
		return

	agent = Agent(server.server, server_type=server.server_type)
	if agent.should_skip_requests():
		return

	pending_jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_id", "status", "callback_failure_count"],
		filters={
			"status": ("in", ["Pending", "Running"]),
			"job_id": ("!=", 0),
			"server": server.server,
		},
		order_by="job_id",
		ignore_ifnull=True,
	)

	if not pending_jobs:
		retry_undelivered_jobs(server)
		add_timer_data_to_monitor(server.server)
		return

	pending_ids = [j.job_id for j in pending_jobs]
	polled_jobs = poll_random_jobs(agent, pending_ids)

	if not polled_jobs:
		retry_undelivered_jobs(server)
		add_timer_data_to_monitor(server.server)
		return

	handle_polled_jobs(polled_jobs, pending_jobs)

	retry_undelivered_jobs(server)
	add_timer_data_to_monitor(server.server)


def handle_polled_job(polled_job, pending_jobs=None, job=None):
	job = job or find(pending_jobs, lambda x: x.job_id == polled_job["id"])
	try:
		# Update Job Status
		# If it is worthy of an update
		if job.status != polled_job["status"]:
			lock_doc_updated_by_job(job.name)
			update_job(job.name, polled_job)

		# Update Steps' Status
		update_steps(job.name, polled_job)
		populate_output_cache(polled_job, job)

		# Some callbacks rely on step statuses, e.g. archive_site
		# so update step status before callbacks are processed
		if polled_job["status"] in ("Success", "Failure", "Undelivered"):
			skip_pending_steps(job.name)
		process_job_updates(job.name, polled_job)

		frappe.db.commit()
		publish_update(job.name)
	except AgentCallbackException:
		# Don't log error for AgentCallbackException
		# it's already logged
		# Rollback all other changes and increment the failure count
		frappe.db.rollback()
		frappe.db.set_value(
			"Agent Job",
			job.name,
			"callback_failure_count",
			job.callback_failure_count + 1,
		)
		frappe.db.commit()
	except Exception:
		log_error(
			"Agent Job Poll Exception",
			job=job,
			polled=polled_job,
			reference_doctype="Agent Job",
			reference_name=job.name,
		)
		frappe.db.rollback()


def populate_output_cache(polled_job, job):
	if not cint(frappe.get_cached_value("Press Settings", None, "realtime_job_updates")):
		return
	steps = frappe.get_all(
		"Agent Job Step",
		filters={"agent_job": job.name, "status": "Running"},
		fields=["name", "step_name"],
	)
	for step in steps:
		polled_step = find(polled_job["steps"], lambda x: x["name"] == step.step_name)
		if polled_step:
			lines = []
			for command in polled_step.get("commands", []):
				output = command.get("output", "").strip()
				if output:
					lines.append(output)
			frappe.cache.hset("agent_job_step_output", step.name, "\n".join(lines))


def filter_active_servers(servers):
	# Prepare list of all_active_servers for each server_type
	# Return servers that are in all_active_servers
	server_types = [server.server_type for server in servers]
	all_active_servers = {}
	for server_type in server_types:
		all_active_servers[server_type] = set(frappe.get_all(server_type, {"status": "Active"}, pluck="name"))

	active_servers = []
	for server in servers:
		if server.server in all_active_servers[server.server_type]:
			active_servers.append(server)

	return active_servers


def filter_request_failures(servers):
	request_failures = set(frappe.get_all("Agent Request Failure", pluck="server"))

	alive_servers = []
	for server in servers:
		if server.server not in request_failures:
			alive_servers.append(server)

	return alive_servers


def poll_pending_jobs():
	"""
	Poll pending job fetches the status of Pending Jobs from all servers.
	"""
	filters = {"status": ("in", ["Pending", "Running", "Undelivered"])}
	if random.random() > 0.1:
		# Experimenting with fewer polls (only for backup jobs)
		# Reduce poll frequency for Backup Site jobs
		# TODO: Replace this with something deterministic
		filters["job_type"] = ("!=", "Backup Site")
	servers = frappe.get_all(
		"Agent Job",
		fields=["server", "server_type"],
		filters=filters,
		group_by="server",
		order_by="",
		ignore_ifnull=True,
	)

	active_servers = filter_active_servers(servers)
	alive_servers = filter_request_failures(active_servers)

	for server in alive_servers:
		frappe.enqueue(
			"press.press.doctype.agent_job.agent_job.poll_pending_jobs_server",
			queue="short",
			server=server,
			job_id=f"poll_pending_jobs:{server.server}",
			deduplicate=True,
		)


def fail_old_jobs():
	def update_status(jobs: list[str], status: str):
		for job in jobs:
			update_job_and_step_status(job, status)
			process_job_updates(job)
		frappe.db.commit()

	failed_jobs = frappe.db.get_values(
		"Agent Job",
		{
			"status": ("in", ["Pending", "Running"]),
			"job_id": ("!=", 0),
			"creation": ("<", add_days(None, -2)),
		},
		"name",
		limit=100,
		pluck=True,
	)
	update_status(failed_jobs, "Failure")

	delivery_failed_jobs = frappe.db.get_values(
		"Agent Job",
		{
			"job_id": 0,
			"creation": ("<", add_days(None, -2)),
			"status": ("!=", "Delivery Failure"),
		},
		"name",
		limit=100,
		pluck=True,
	)

	update_status(delivery_failed_jobs, "Delivery Failure")


def get_pair_jobs():
	"""Return list of jobs who's callback depend on another"""
	return (
		"New Site",
		"New Site from Backup",
		"Add Site to Upstream",
		"Archive Site",
		"Remove Site from Upstream",
		"Rename Site",
		"Rename Site on Upstream",
		"Add User to ProxySQL",
		"Remove User from ProxySQL",
	)


def lock_doc_updated_by_job(job_name):
	"""
	Ensure serializability of callback of jobs associated with the same document

	All select queries in this transaction should have for_update True for this to work correctly
	"""
	field_values = frappe.db.get_values(
		"Agent Job",
		job_name,
		["site", "bench", "server", "server_type", "job_type"],
		as_dict=True,
	)[0]  # relies on order of values to be site, bench..

	if field_values["job_type"] not in get_pair_jobs():
		return None

	for field, value in field_values.items():
		doctype = field.capitalize()
		if field == "server":
			doctype = field_values["server_type"]
		elif field in (
			"server_type",
			"job_type",
		):  # ideally will never happen, but for sanity
			return None
		if value:
			frappe.db.get_value(doctype, value, "modified", for_update=True)
			return value

	return None


def update_job(job_name, job):
	job_data = json.dumps(job["data"], indent=4, sort_keys=True)
	frappe.db.set_value(
		"Agent Job",
		job_name,
		{
			"start": job["start"],
			"end": job["end"],
			"duration": job["duration"],
			"status": job["status"],
			"data": job_data,
			"output": job["data"].get("output"),
			"traceback": job["data"].get("traceback"),
		},
	)


def update_steps(job_name, job):
	step_names = [polled_step["name"] for polled_step in job["steps"]]
	steps = frappe.db.get_all(
		"Agent Job Step",
		fields=["name", "status", "step_name"],
		filters={
			"agent_job": job_name,
			"status": ("in", ["Pending", "Running"]),
			"step_name": ("in", step_names),
		},
	)
	for polled_step in job["steps"]:
		step = find(steps, lambda x: x.step_name == polled_step["name"])
		if not step:
			continue

		if step.status == polled_step["status"]:
			continue

		lock_doc_updated_by_job(job_name)
		update_step(step.name, polled_step)


def update_step(step_name, step):
	step_data = json.dumps(step["data"], indent=4, sort_keys=True)

	output = None
	traceback = None
	if isinstance(step["data"], dict):
		traceback = to_str(step["data"].get("traceback", ""))
		output = to_str(step["data"].get("output", ""))

	frappe.db.set_value(
		"Agent Job Step",
		step_name,
		{
			"start": step["start"],
			"end": step["end"],
			"duration": step["duration"],
			"status": step["status"],
			"data": step_data,
			"output": output,
			"traceback": traceback,
		},
	)


def skip_pending_steps(job_name):
	frappe.db.sql(
		"""UPDATE  `tabAgent Job Step` SET  status = 'Skipped'
		WHERE status = 'Pending' AND agent_job = %s""",
		job_name,
	)


def get_next_retry_at(job_retry_count):
	from frappe.utils import add_to_date, now_datetime

	backoff_in_seconds = 5
	retry_in_seconds = job_retry_count**backoff_in_seconds

	return add_to_date(now_datetime(), seconds=retry_in_seconds)


@timer
def retry_undelivered_jobs(server):
	"""Retry undelivered jobs and update job status if max retry count is reached"""

	if is_auto_retry_disabled(server):
		return

	job_types, max_retry_per_job_type = get_retryable_job_types_and_max_retry_count()
	server_jobs = get_undelivered_jobs_for_server(server, job_types)
	nowtime = now_datetime()

	for server in server_jobs:
		delivered_jobs = get_jobs_delivered_to_server(server, server_jobs[server])

		if delivered_jobs:
			update_job_ids_for_delivered_jobs(delivered_jobs)

		undelivered_jobs = list(set(server_jobs[server]) - set(delivered_jobs))

		for job_name in undelivered_jobs:
			job = AgentJob("Agent Job", job_name)
			max_retry_count = max_retry_per_job_type[job.job_type] or 0

			if not job.next_retry_at and job.name not in queued_jobs():
				job.set_status_and_next_retry_at()
				continue

			if get_datetime(job.next_retry_at) > nowtime:
				continue

			if job.retry_count <= max_retry_count:
				retry = job.retry_count + 1
				frappe.db.set_value("Agent Job", job_name, "retry_count", retry, update_modified=False)
				job.retry_in_place()
			else:
				update_job_and_step_status(job_name, "Delivery Failure")
				process_job_updates(job_name)


def queued_jobs():
	from frappe.utils.background_jobs import get_jobs

	return get_jobs(site=frappe.local.site, queue="default", key="name")[frappe.local.site]


def is_auto_retry_disabled(server):
	"""Check if auto retry is disabled for the server"""
	_auto_retry_disabled = False

	# Global Config
	_auto_retry_disabled = frappe.db.get_single_value("Press Settings", "disable_auto_retry", cache=True)
	if _auto_retry_disabled:
		return True

	# Server Config
	try:
		_auto_retry_disabled = frappe.db.get_value(
			server.server_type,
			server.server,
			"disable_agent_job_auto_retry",
			cache=True,
		)
	except Exception:
		_auto_retry_disabled = False

	return _auto_retry_disabled


def update_job_and_step_status(job: str, status: str):
	agent_job = frappe.qb.DocType("Agent Job")
	frappe.qb.update(agent_job).set(agent_job.status, status).where(agent_job.name == job).run()

	agent_job_step = frappe.qb.DocType("Agent Job Step")
	frappe.qb.update(agent_job_step).set(agent_job_step.status, status).where(
		agent_job_step.agent_job == job
	).run()


def get_undelivered_jobs_for_server(server, job_types):
	jobs = frappe._dict()

	if not job_types:
		return jobs

	for job in frappe.get_all(
		"Agent Job",
		{
			"status": "Undelivered",
			"job_id": 0,
			"server": server.server,
			"server_type": server.server_type,
			"retry_count": (">", 0),
			"job_type": ("in", job_types),
		},
		["name", "job_type"],
		ignore_ifnull=True,  # job type is mandatory and next_retry_at has to be set for retry
	):
		jobs.setdefault((server.server, server.server_type), []).append(job["name"])

	return jobs


def get_server_wise_undelivered_jobs(job_types):
	jobs = frappe._dict()

	if not job_types:
		return jobs

	for job in frappe.get_all(
		"Agent Job",
		{
			"status": "Undelivered",
			"job_id": 0,
			"retry_count": [">=", 1],
			"next_retry_at": ("<=", frappe.utils.now_datetime()),
			"job_type": ("in", job_types),
		},
		["name", "server", "server_type"],
		ignore_ifnull=True,  # job type is mandatory and next_retry_at has to be set for retry
	):
		jobs.setdefault((job.server, job.server_type), []).append(job["name"])

	return jobs


def get_jobs_delivered_to_server(server, jobs):
	agent = Agent(server[0], server_type=server[1])

	random_undelivered_ids = random.sample(jobs, k=min(100, len(jobs)))
	delivered_jobs = agent.get_jobs_id(random_undelivered_ids)

	return delivered_jobs or []


def update_job_ids_for_delivered_jobs(delivered_jobs):
	for job in delivered_jobs:
		frappe.db.set_value(
			"Agent Job",
			job["agent_job_id"],
			{
				"job_id": job["id"],
				"status": "Pending",
				"next_retry_at": None,
				"retry_count": 0,
			},
			update_modified=False,
		)


def is_site_archived(site: str | None) -> bool:
	if not site:
		return False
	return frappe.db.get_value("Site", site, "status") == "Archived"


def process_job_updates(job_name: str, response_data: dict | None = None):  # noqa: C901
	job: "AgentJob" = frappe.get_doc("Agent Job", job_name)
	start = now_datetime()

	try:
		from press.press.doctype.agent_job.agent_job_notifications import (
			send_job_failure_notification,
		)
		from press.press.doctype.app_patch.app_patch import AppPatch
		from press.press.doctype.bench.bench import (
			Bench,
			process_add_ssh_user_job_update,
			process_archive_bench_job_update,
			process_new_bench_job_update,
			process_remove_ssh_user_job_update,
		)
		from press.press.doctype.code_server.code_server import (
			process_archive_code_server_job_update,
			process_new_code_server_job_update,
			process_start_code_server_job_update,
			process_stop_code_server_job_update,
		)
		from press.press.doctype.database_server.database_server import (
			process_add_binlogs_to_indexer_agent_job_update,
			process_remove_binlogs_from_indexer_agent_job_update,
		)
		from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
		from press.press.doctype.logical_replication_backup.logical_replication_backup import (
			process_logical_replication_backup_activate_site_job_update,
			process_logical_replication_backup_deactivate_site_job_update,
			process_logical_replication_backup_update_database_host_job_update,
		)
		from press.press.doctype.mariadb_binlog.mariadb_binlog import (
			process_upload_binlogs_to_s3_job_update,
		)
		from press.press.doctype.physical_backup_restoration.physical_backup_restoration import (
			process_job_update as process_physical_backup_restoration_job_update,
		)
		from press.press.doctype.physical_backup_restoration.physical_backup_restoration import (
			process_physical_backup_restoration_deactivate_site_job_update,
		)
		from press.press.doctype.proxy_server.proxy_server import (
			process_update_nginx_job_update,
		)
		from press.press.doctype.server.server import process_new_server_job_update
		from press.press.doctype.server_snapshot_recovery.server_snapshot_recovery import (
			process_backup_database_from_snapshot_job_callback,
			process_backup_files_from_snapshot_job_callback,
			process_search_sites_in_snapshot_job_callback,
		)
		from press.press.doctype.site.erpnext_site import (
			process_setup_erpnext_site_job_update,
		)
		from press.press.doctype.site.site import (
			process_add_domain_job_update,
			process_archive_site_job_update,
			process_complete_setup_wizard_job_update,
			process_create_user_job_update,
			process_fetch_database_table_schema_job_update,
			process_install_app_site_job_update,
			process_migrate_site_job_update,
			process_move_site_to_bench_job_update,
			process_new_site_job_update,
			process_reinstall_site_job_update,
			process_rename_site_job_update,
			process_restore_job_update,
			process_restore_tables_job_update,
			process_uninstall_app_site_job_update,
		)
		from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
		from press.press.doctype.site_backup.site_backup import (
			process_deactivate_site_job_update as process_site_backup_deactivate_site_job_update,
		)
		from press.press.doctype.site_domain.site_domain import (
			process_add_domain_to_upstream_job_update,
			process_new_host_job_update,
		)
		from press.press.doctype.site_update.site_update import (
			process_activate_site_job_update,
			process_deactivate_site_job_update,
			process_update_site_job_update,
			process_update_site_recover_job_update,
		)

		site_migration = get_ongoing_migration(job.site)
		if site_migration:
			process_site_migration_job_update(
				job, site_migration
			)  # has to be at top to prevent regular callbacks from running
		elif is_site_archived(job.site):
			return
		elif job.job_type == "Add Upstream to Proxy":
			process_new_server_job_update(job)
		elif job.job_type == "New Bench":
			process_new_bench_job_update(job)
		elif job.job_type == "Archive Bench":
			process_archive_bench_job_update(job)
		elif job.job_type == "New Site":
			process_new_site_job_update(job)
		elif job.job_type == "New Site from Backup":
			process_new_site_job_update(job)
			process_restore_job_update(job, force=True)
		elif job.job_type == "Restore Site":
			process_restore_job_update(job)
		elif job.job_type == "Reinstall Site":
			process_reinstall_site_job_update(job)
		elif job.job_type == "Migrate Site":
			process_migrate_site_job_update(job)
		elif job.job_type == "Install App on Site":
			process_install_app_site_job_update(job)
		elif job.job_type == "Uninstall App from Site":
			process_uninstall_app_site_job_update(job)
		elif job.job_type == "Add Site to Upstream":
			process_new_site_job_update(job)
		elif job.job_type == "Add Code Server to Upstream" or job.job_type == "Setup Code Server":
			process_new_code_server_job_update(job)
		elif job.job_type == "Start Code Server":
			process_start_code_server_job_update(job)
		elif job.job_type == "Stop Code Server":
			process_stop_code_server_job_update(job)
		elif job.job_type == "Archive Code Server" or job.job_type == "Remove Code Server from Upstream":
			process_archive_code_server_job_update(job)
		elif job.job_type in ["Backup Site", "Physical Backup Database"]:
			process_backup_site_job_update(job)
		elif job.job_type == "Archive Site" or job.job_type == "Remove Site from Upstream":
			process_archive_site_job_update(job)
		elif job.job_type == "Add Host to Proxy":
			process_new_host_job_update(job)
		elif job.job_type == "Add Domain to Upstream":
			process_add_domain_to_upstream_job_update(job)
		elif job.job_type == "Update Site Migrate" or job.job_type == "Update Site Pull":
			process_update_site_job_update(job)
		elif (
			job.job_type == "Recover Failed Site Migrate"
			or job.job_type == "Recover Failed Site Pull"
			or job.job_type == "Recover Failed Site Update"
		):
			process_update_site_recover_job_update(job)
		elif job.job_type == "Rename Site" or job.job_type == "Rename Site on Upstream":
			process_rename_site_job_update(job)
		elif job.job_type == "Setup ERPNext":
			process_setup_erpnext_site_job_update(job)
		elif job.job_type == "Restore Site Tables":
			process_restore_tables_job_update(job)
		elif job.job_type == "Add User to Proxy":
			process_add_ssh_user_job_update(job)
		elif job.job_type == "Remove User from Proxy":
			process_remove_ssh_user_job_update(job)
		elif job.job_type == "Add User to ProxySQL" or job.job_type == "Remove User from ProxySQL":
			if job.reference_doctype == "Site Database User":
				SiteDatabaseUser.process_job_update(job)
		elif job.job_type == "Reload NGINX":
			process_update_nginx_job_update(job)
		elif job.job_type == "Move Site to Bench":
			process_move_site_to_bench_job_update(job)
		elif job.job_type == "Patch App":
			AppPatch.process_patch_app(job)
		elif job.job_type == "Run Remote Builder":
			DeployCandidateBuild.process_run_build(job, response_data)
		elif job.job_type == "Create User":
			process_create_user_job_update(job)
		elif job.job_type == "Complete Setup Wizard":
			process_complete_setup_wizard_job_update(job)
		elif job.job_type == "Update Bench In Place":
			Bench.process_update_inplace(job)
		elif job.job_type == "Recover Update In Place":
			Bench.process_recover_update_inplace(job)
		elif job.job_type == "Fetch Database Table Schema":
			process_fetch_database_table_schema_job_update(job)
		elif job.job_type in [
			"Create Database User",
			"Remove Database User",
			"Modify Database User Permissions",
		]:
			SiteDatabaseUser.process_job_update(job)
		elif job.job_type == "Physical Restore Database":
			process_physical_backup_restoration_job_update(job)
		elif job.job_type == "Deactivate Site" and job.reference_doctype == "Site Update":
			process_deactivate_site_job_update(job)
		elif job.job_type == "Activate Site" and job.reference_doctype == "Site Update":
			process_activate_site_job_update(job)
		elif job.job_type == "Activate Site" and job.reference_doctype == "Logical Replication Backup":
			process_logical_replication_backup_activate_site_job_update(job)
		elif job.job_type == "Deactivate Site" and job.reference_doctype == "Site Backup":
			process_site_backup_deactivate_site_job_update(job)
		elif job.job_type == "Deactivate Site" and job.reference_doctype == "Physical Backup Restoration":
			process_physical_backup_restoration_deactivate_site_job_update(job)
		elif job.job_type == "Deactivate Site" and job.reference_doctype == "Logical Replication Backup":
			process_logical_replication_backup_deactivate_site_job_update(job)
		elif job.job_type == "Update Database Host" and job.reference_doctype == "Logical Replication Backup":
			process_logical_replication_backup_update_database_host_job_update(job)
		elif job.job_type == "Add Domain":
			process_add_domain_job_update(job)
		elif job.job_type == "Add Binlogs To Indexer":
			process_add_binlogs_to_indexer_agent_job_update(job)
		elif job.job_type == "Remove Binlogs From Indexer":
			process_remove_binlogs_from_indexer_agent_job_update(job)
		elif job.job_type == "Upload Binlogs To S3":
			process_upload_binlogs_to_s3_job_update(job)
		elif job.job_type == "Search Sites In Snapshot":
			process_search_sites_in_snapshot_job_callback(job)
		elif job.job_type == "Backup Database From Snapshot":
			process_backup_database_from_snapshot_job_callback(job)
		elif job.job_type == "Backup Files From Snapshot":
			process_backup_files_from_snapshot_job_callback(job)

		# send failure notification if job failed
		if job.status == "Failure":
			send_job_failure_notification(job)

		log_update(job, start)
	except Exception as e:
		failure_count = job.callback_failure_count + 1
		if failure_count in set([10, 100]) or failure_count % 1000 == 0:
			log_error(
				"Agent Job Callback Exception",
				job=job.as_dict(),
				reference_doctype="Agent Job",
				reference_name=job_name,
			)
		log_update(job, start, e)
		raise AgentCallbackException from e


def log_update(job, start, exception=None):
	try:
		data = {
			"timestamp": start,
			"duration": (now_datetime() - start).total_seconds(),
			"name": job.name,
			"job_type": job.job_type,
			"status": job.status,
			"server": job.server,
			"site": job.site,
			"bench": job.bench,
		}
		if exception:
			data["exception"] = exception
		serialized = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
		frappe.cache().rpush(AGENT_LOG_KEY, serialized)
	except Exception:
		traceback.print_exc()


def update_job_step_status():
	from frappe.query_builder.custom import GROUP_CONCAT

	agent_job = frappe.qb.DocType("Agent Job")
	agent_job_step = frappe.qb.DocType("Agent Job Step")

	steps_to_update = (
		frappe.qb.from_(agent_job)
		.join(agent_job_step)
		.on(agent_job.name == agent_job_step.agent_job)
		.select(
			agent_job.name.as_("agent_job"),
			agent_job.status.as_("job_status"),
			GROUP_CONCAT(agent_job_step.name, alias="step_names"),
		)
		.where(
			(agent_job.status.isin(["Failure", "Delivery Failure"])) & (agent_job_step.status == "Pending")
		)
		.groupby(agent_job.name)
		.limit(100)
	).run(as_dict=True)

	for step in steps_to_update:
		(
			frappe.qb.update(agent_job_step)
			.where(
				(agent_job_step.agent_job == step.agent_job)
				& (agent_job_step.name.isin(step.step_names.split(",")))
				& (agent_job_step.status.isin(["Pending", "Running"]))
			)
			.set(agent_job_step.status, step.job_status)
		).run()


def on_doctype_update():
	frappe.db.add_index("Agent Job", ["status", "server"])
	frappe.db.add_index("Agent Job", ["reference_doctype", "reference_name"])
	# We don't need modified index, it's harmful on constantly updating tables
	frappe.db.sql_ddl("drop index if exists modified on `tabAgent Job`")
	frappe.db.add_index("Agent Job", ["creation"])


def to_str(data) -> str:
	if isinstance(data, str):
		return data

	try:
		return json.dumps(data, default=str)
	except Exception:
		pass

	try:
		return str(data)
	except Exception:
		return ""


def flush():
	log_file = os.path.join(frappe.utils.get_bench_path(), "logs", f"{AGENT_LOG_KEY}.json.log")
	try:
		# Fetch all entries without removing from cache
		logs = frappe.cache().lrange(AGENT_LOG_KEY, 0, -1)
		print("LOGS", logs)
		if logs:
			logs = list(map(frappe.safe_decode, logs))
			with open(log_file, "a", os.O_NONBLOCK) as f:
				f.write("\n".join(logs))
				f.write("\n")
			# Remove fetched entries from cache
			frappe.cache().ltrim(AGENT_LOG_KEY, len(logs) - 1, -1)
	except Exception:
		traceback.print_exc()


def update_query_result_status_timestamps(results):
	for result in results:
		if result.status == "Undelivered":
			result.status = "Pending"
		elif result.status == "Delivery Failure":
			result.status = "Failure"

		# agent job start and end are in utc
		if result.start:
			result.start = convert_utc_to_system_timezone(result.start).replace(tzinfo=None)

		if result.end:
			result.end = convert_utc_to_system_timezone(result.end).replace(tzinfo=None)


def agent_poll_count_stats(from_datetime, to_datetime, min_count, duration):
	rows = frappe.get_all(
		"Scheduled Job Log",
		filters=[
			["creation", ">=", from_datetime],
			["creation", "<", to_datetime],
			["scheduled_job_type", "=", "agent_job.poll_pending_jobs"],
		],
		fields=["DATE_FORMAT(creation, '%Y-%m-%d %H:%i:00') as timestamp", "count(*) as count"],
		order_by="timestamp ASC",
		group_by="timestamp",
	)
	found = {frappe.utils.get_datetime(row["timestamp"]): row["count"] for row in rows}
	total_count = sum(found.values())
	average_count = total_count / len(found)
	filtered_data = {key: value for key, value in found.items() if value < 10}
	sorted_dict = dict(sorted(filtered_data.items(), key=lambda item: item[1]))
	top_min_count = dict(list(sorted_dict.items())[:min_count])

	telegram_message = f"""Agent Polling Count {duration} Report

	Average Count: {average_count:.2f}

	Top {min_count} Minimum Values (≤10):
	"""

	if top_min_count:
		for i, item in enumerate(top_min_count, 1):
			timestamp_str = frappe.utils.format_datetime(item, "dd MMM yyyy, HH:mm")
			telegram_message = telegram_message + f"\n{i}. 🕒 {timestamp_str} → Count: {top_min_count[item]}"
	else:
		telegram_message = telegram_message + "\nNo entries found with count ≤ 10"

	telegram_message = telegram_message + f"\n\nFound {len(filtered_data)} entries with count ≤ 10"
	TelegramMessage.enqueue(message=telegram_message, topic="Signups")


def agent_poll_count_stats_hourly():
	min_count = 3
	duration = "Hourly"
	start_time = frappe.utils.add_to_date(None, hours=-1)
	end_time = frappe.utils.add_to_date(None, minutes=-1)
	agent_poll_count_stats(start_time, end_time, min_count, duration)


def agent_poll_count_stats_daily():
	min_count = 12
	duration = "Daily"
	start_time = frappe.utils.add_to_date(None, hours=-24)
	end_time = frappe.utils.add_to_date(None, minutes=-1)
	agent_poll_count_stats(start_time, end_time, min_count, duration)
