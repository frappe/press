# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import random

from press.press.doctype.deploy_candidate.deploy_candidate import (
	process_docker_image_build_job_update,
)
import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	cint,
	convert_utc_to_system_timezone,
	create_batch,
	cstr,
)

from press.agent import Agent
from press.api.client import is_owned_by_team
from press.press.doctype.press_notification.press_notification import (
	create_new_notification,
)
from press.press.doctype.site_migration.site_migration import (
	get_ongoing_migration,
	process_site_migration_job_update,
)
from press.utils import log_error


class AgentJob(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link | None
		code_server: DF.Link | None
		data: DF.Code | None
		duration: DF.Time | None
		end: DF.Datetime | None
		host: DF.Link | None
		job_id: DF.Int
		job_type: DF.Link
		next_retry_at: DF.Datetime | None
		output: DF.Code | None
		request_data: DF.Code
		request_files: DF.Code | None
		request_method: DF.Literal["GET", "POST", "DELETE"]
		request_path: DF.Data
		retry_count: DF.Int
		server: DF.DynamicLink
		server_type: DF.Link
		site: DF.Link | None
		start: DF.Datetime | None
		status: DF.Literal[
			"Undelivered", "Pending", "Running", "Success", "Failure", "Delivery Failure"
		]
		traceback: DF.Code | None
		upstream: DF.Link | None
	# end: auto-generated types

	dashboard_fields = [
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
	]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		site = cstr(filters.get("site", ""))
		group = cstr(filters.get("group", ""))
		server = cstr(filters.get("server", ""))

		if not (site or group or server):
			frappe.throw("Not permitted", frappe.PermissionError)

		if site:
			is_owned_by_team("Site", site, raise_exception=True)

		if group:
			is_owned_by_team("Release Group", group, raise_exception=True)
			AgentJob = frappe.qb.DocType("Agent Job")
			Bench = frappe.qb.DocType("Bench")
			benches = (
				frappe.qb.from_(Bench).select(Bench.name).where(Bench.group == filters.group)
			)
			query = query.where(AgentJob.bench.isin(benches))

		if server:
			is_owned_by_team("Server", server, raise_exception=True)

		results = query.run(as_dict=1)
		for result in results:
			if result.status == "Undelivered":
				result.status = "Pending"
			# agent job start and end are in utc
			if result.start:
				result.start = convert_utc_to_system_timezone(result.start).replace(tzinfo=None)
			if result.end:
				result.end = convert_utc_to_system_timezone(result.end).replace(tzinfo=None)
		return results

	def get_doc(self, doc):
		if doc.status == "Undelivered":
			doc.status = "Pending"

		doc["steps"] = frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": self.name},
			fields=["name", "step_name", "status", "start", "end", "duration", "output"],
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
		self.enqueue_http_request()

	def enqueue_http_request(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"create_http_request",
			timeout=600,
			enqueue_after_commit=True,
		)

	def create_http_request(self):
		try:
			agent = Agent(self.server, server_type=self.server_type)
			data = json.loads(self.request_data)
			files = json.loads(self.request_files)

			self.job_id = agent.request(
				self.request_method, self.request_path, data, files, agent_job=self
			)["job"]

			self.status = "Pending"
			self.save()
		except Exception:
			if 400 <= cint(self.flags.status_code) <= 499:
				self.status = "Failure"
				self.save()
				process_job_updates(self.name)

			else:
				self.set_status_and_next_retry_at()

	def set_status_and_next_retry_at(self):
		try:
			next_retry_at = get_next_retry_at(self.retry_count)

			if not self.retry_count:
				self.retry_count = 1

			frappe.db.set_value(
				"Agent Job",
				self.name,
				{
					"status": "Undelivered",
					"next_retry_at": next_retry_at,
					"retry_count": self.retry_count,
				},
				update_modified=False,
			)
		except Exception:
			log_error(
				"Agent Job Set Status Exception",
				job=self,
				reference_doctype="Agent Job",
				reference_name=self.name,
			)

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
		job = frappe.get_doc(
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
		return job

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

	def on_trash(self):
		steps = frappe.get_all("Agent Job Step", filters={"agent_job": self.name})
		for step in steps:
			frappe.delete_doc("Agent Job Step", step.name)

		frappe.db.delete(
			"Press Notification",
			{"document_type": self.doctype, "document_name": self.name},
		)


def job_detail(job):
	job = frappe.get_doc("Agent Job", job)
	steps = []
	current = {}
	for index, job_step in enumerate(
		frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": job.name},
			fields=["step_name", "status"],
			order_by="creation",
		)
	):
		step = {"name": job_step.step_name, "status": job_step.status, "index": index}
		if job_step.status == "Running":
			current = step
		steps.append(step)

	if job.status == "Pending":
		current = {"name": job.job_type, "status": "Waiting", "index": -1}
	elif job.status in ("Success", "Failure"):
		current = {"name": job.job_type, "status": job.status, "index": len(steps)}

	current["total"] = len(steps)

	message = {
		"id": job.name,
		"name": job.job_type,
		"server": job.server,
		"bench": job.bench,
		"site": job.site,
		"status": job.status,
		"steps": steps,
		"current": current,
	}
	return message


def publish_update(job):
	message = job_detail(job)
	job_owner = frappe.db.get_value("Agent Job", job, "owner")
	frappe.publish_realtime(event="agent_job_update", message=message, user=job_owner)


def suspend_sites():
	"""Suspend sites if they have exceeded database or disk limits"""

	if not frappe.db.get_single_value("Press Settings", "enforce_storage_limits"):
		return

	free_teams = frappe.get_all(
		"Team", filters={"free_account": True, "enabled": True}, pluck="name"
	)
	active_sites = frappe.get_all(
		"Site",
		filters={"status": "Active", "free": False, "team": ("not in", free_teams)},
		fields=["name", "team", "current_database_usage", "current_disk_usage"],
	)

	issue_reload = False
	for site in active_sites:
		if site.current_database_usage > 100 or site.current_disk_usage > 100:
			frappe.get_doc("Site", site.name).suspend(
				reason="Site Usage Exceeds Plan limits", skip_reload=True
			)
			issue_reload = True

	if issue_reload:
		proxies = frappe.get_all("Proxy Server", {"status": "Active"}, pluck="name")
		for proxy_name in proxies:
			agent = Agent(proxy_name, server_type="Proxy Server")
			agent.reload_nginx()


def poll_pending_jobs_server(server):
	if frappe.db.get_value(server.server_type, server.server, "status") != "Active":
		return

	pending_jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_id", "status"],
		filters={
			"status": ("in", ["Pending", "Running"]),
			"job_id": ("!=", 0),
			"server": server.server,
		},
		order_by="job_id",
		ignore_ifnull=True,
	)

	if not pending_jobs:
		return

	agent = Agent(server.server, server_type=server.server_type)

	pending_ids = [j.job_id for j in pending_jobs]
	random_pending_ids = random.sample(pending_ids, k=min(100, len(pending_ids)))
	polled_jobs = agent.get_jobs_status(random_pending_ids)

	if not polled_jobs:
		return

	for polled_job in polled_jobs:
		if not polled_job:
			continue
		job = find(pending_jobs, lambda x: x.job_id == polled_job["id"])
		try:
			# Update Job Status
			# If it is worthy of an update
			if job.status != polled_job["status"]:
				lock_doc_updated_by_job(job.name)
				update_job(job.name, polled_job)

			# Update Steps' Status
			update_steps(job.name, polled_job)
			populate_output_cache(polled_job, job)
			process_job_updates(job.name)
			if polled_job["status"] in ("Success", "Failure", "Undelivered"):
				skip_pending_steps(job.name)

			frappe.db.commit()
			publish_update(job.name)
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


def poll_pending_jobs():
	servers = frappe.get_all(
		"Agent Job",
		fields=["server", "server_type", "count(*) as count"],
		filters={"status": ("in", ["Pending", "Running"]), "job_id": ("!=", 0)},
		group_by="server",
		order_by="count desc",
		ignore_ifnull=True,
	)

	for server in servers:
		server.pop("count")
		frappe.enqueue(
			"press.press.doctype.agent_job.agent_job.poll_pending_jobs_server",
			queue="short",
			server=server,
			job_id=f"poll_pending_jobs:{server.server}",
			deduplicate=True,
		)


def fail_old_jobs():
	def update_status(jobs: list[str], status: str):
		for batch in create_batch(jobs or [], 100):
			frappe.db.set_value("Agent Job", {"name": ("in", batch)}, "status", status)
			frappe.db.commit()

	failed_jobs = frappe.db.get_values(
		"Agent Job",
		{
			"status": ("in", ["Pending", "Running"]),
			"job_id": ("!=", 0),
			"modified": ("<", add_days(None, -2)),
		},
		"name",
		pluck=True,
	)
	update_status(failed_jobs, "Failure")

	undelivered_jobs = frappe.db.get_values(
		"Agent Job",
		{
			"job_id": 0,
			"modified": ("<", add_days(None, -2)),
			"status": ("!=", "Undelivered"),
		},
		"name",
		pluck=True,
	)

	update_status(undelivered_jobs, "Undelivered")


def get_pair_jobs() -> tuple[str]:
	"""Return list of jobs who's callback depend on another"""
	return (
		"New Site",
		"New Site from Backup",
		"Add Site to Upstream",
		"Archive Site",
		"Remove Site from Upstream",
		"Rename Site",
		"Rename Site on Upstream",
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
	)[
		0
	]  # relies on order of values to be site, bench..

	if field_values["job_type"] not in get_pair_jobs():
		return

	for field, value in field_values.items():
		doctype = field.capitalize()
		if field == "server":
			doctype = field_values["server_type"]
		elif field in (
			"server_type",
			"job_type",
		):  # ideally will never happen, but for sanity
			return
		if value:
			frappe.db.get_value(doctype, value, "modified", for_update=True)
			return value


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

	# send notification if job failed
	if job["status"] == "Failure":
		job_site, job_type = frappe.db.get_value("Agent Job", job_name, ["site", "job_type"])
		notification_type, message = "", ""

		if job_type == "Update Site Migrate":
			notification_type = "Site Migrate"
			message = f"Site <b>{job_site}</b> failed to migrate"
		elif job_type == "Update Site Pull":
			notification_type = "Site Update"
			message = f"Site <b>{job_site}</b> failed to update"
		elif job_type.startswith("Recover Failed"):
			notification_type = "Site Recovery"
			message = f"Site <b>{job_site}</b> failed to recover after a failed update/migration"

		if notification_type:
			create_new_notification(
				frappe.get_value("Site", job_site, "team"),
				notification_type,
				"Agent Job",
				job_name,
				message,
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
		if step and step.status != polled_step["status"]:
			lock_doc_updated_by_job(job_name)
			update_step(step.name, polled_step)


def update_step(step_name, step):
	step_data = json.dumps(step["data"], indent=4, sort_keys=True)
	frappe.db.set_value(
		"Agent Job Step",
		step_name,
		{
			"start": step["start"],
			"end": step["end"],
			"duration": step["duration"],
			"status": step["status"],
			"data": step_data,
			"output": step["data"].get("output"),
			"traceback": step["data"].get("traceback"),
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

	backoff_in_seconds = 2
	retry_in_seconds = job_retry_count**backoff_in_seconds

	return add_to_date(now_datetime(), seconds=retry_in_seconds)


def retry_undelivered_jobs():
	job_types, max_retry_per_job_type = get_retryable_job_types_and_max_retry_count()
	server_jobs = get_server_wise_undelivered_jobs(job_types)

	for server in server_jobs:
		delivered_jobs = get_jobs_delivered_to_server(server, server_jobs[server])

		if delivered_jobs:
			update_job_ids_for_delivered_jobs(delivered_jobs)

		undelivered_jobs = list(set(server_jobs[server]) - set(delivered_jobs))

		for job in undelivered_jobs:
			job_doc = frappe.get_doc("Agent Job", job)
			max_retry_count = max_retry_per_job_type[job_doc.job_type] or 0

			if job_doc.retry_count < max_retry_count:
				retry = job_doc.retry_count + 1
				frappe.db.set_value("Agent Job", job, "retry_count", retry, update_modified=False)
				job_doc.retry_in_place()
			else:
				update_job_and_step_status(job)


def get_retryable_job_types_and_max_retry_count():
	job_types, max_retry_per_job_type = [], {}
	for job_type in frappe.get_all(
		"Agent Job Type",
		filters={"disabled_auto_retry": 0, "max_retry_count": [">", 0]},
		fields=["name", "max_retry_count"],
	):
		job_types.append(job_type["name"])
		max_retry_per_job_type[job_type["name"]] = job_type["max_retry_count"]

	return job_types, max_retry_per_job_type


def update_job_and_step_status(job):
	agent_job = frappe.qb.DocType("Agent Job")
	frappe.qb.update(agent_job).set(agent_job.status, "Delivery Failure").where(
		agent_job.name == job
	).run()

	agent_job_step = frappe.qb.DocType("Agent Job Step")
	frappe.qb.update(agent_job_step).set(agent_job_step.status, "Delivery Failure").where(
		agent_job_step.agent_job == job
	).run()

	process_job_updates(job)


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


def process_job_updates(job_name):
	job = frappe.get_doc("Agent Job", job_name)
	try:
		from press.press.doctype.bench.bench import (
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
		from press.press.doctype.proxy_server.proxy_server import (
			process_update_nginx_job_update,
		)
		from press.press.doctype.server.server import process_new_server_job_update
		from press.press.doctype.site.erpnext_site import (
			process_setup_erpnext_site_job_update,
		)
		from press.press.doctype.site.site import (
			process_add_proxysql_user_job_update,
			process_archive_site_job_update,
			process_install_app_site_job_update,
			process_migrate_site_job_update,
			process_move_site_to_bench_job_update,
			process_new_site_job_update,
			process_reinstall_site_job_update,
			process_remove_proxysql_user_job_update,
			process_rename_site_job_update,
			process_restore_job_update,
			process_restore_tables_job_update,
			process_uninstall_app_site_job_update,
		)
		from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
		from press.press.doctype.site_domain.site_domain import process_new_host_job_update
		from press.press.doctype.site_update.site_update import (
			process_update_site_job_update,
			process_update_site_recover_job_update,
		)
		from press.press.doctype.app_patch.app_patch import AppPatch

		site_migration = get_ongoing_migration(job.site)
		if site_migration:
			process_site_migration_job_update(job, site_migration)
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
		elif job.job_type == "Add Code Server to Upstream":
			process_new_code_server_job_update(job)
		elif job.job_type == "Setup Code Server":
			process_new_code_server_job_update(job)
		elif job.job_type == "Start Code Server":
			process_start_code_server_job_update(job)
		elif job.job_type == "Stop Code Server":
			process_stop_code_server_job_update(job)
		elif job.job_type == "Archive Code Server":
			process_archive_code_server_job_update(job)
		elif job.job_type == "Remove Code Server from Upstream":
			process_archive_code_server_job_update(job)
		elif job.job_type == "Backup Site":
			process_backup_site_job_update(job)
		elif job.job_type == "Archive Site":
			process_archive_site_job_update(job)
		elif job.job_type == "Remove Site from Upstream":
			process_archive_site_job_update(job)
		elif job.job_type == "Add Host to Proxy":
			process_new_host_job_update(job)
		elif job.job_type == "Update Site Migrate":
			process_update_site_job_update(job)
		elif job.job_type == "Update Site Pull":
			process_update_site_job_update(job)
		elif job.job_type == "Recover Failed Site Migrate":
			process_update_site_recover_job_update(job)
		elif job.job_type == "Recover Failed Site Pull":
			process_update_site_recover_job_update(job)
		elif job.job_type == "Recover Failed Site Update":
			process_update_site_recover_job_update(job)
		elif job.job_type == "Rename Site":
			process_rename_site_job_update(job)
		elif job.job_type == "Rename Site on Upstream":
			process_rename_site_job_update(job)
		elif job.job_type == "Setup ERPNext":
			process_setup_erpnext_site_job_update(job)
		elif job.job_type == "Restore Site Tables":
			process_restore_tables_job_update(job)
		elif job.job_type == "Add User to Proxy":
			process_add_ssh_user_job_update(job)
		elif job.job_type == "Remove User from Proxy":
			process_remove_ssh_user_job_update(job)
		elif job.job_type == "Add User to ProxySQL":
			process_add_proxysql_user_job_update(job)
		elif job.job_type == "Remove User from ProxySQL":
			process_remove_proxysql_user_job_update(job)
		elif job.job_type == "Reload NGINX":
			process_update_nginx_job_update(job)
		elif job.job_type == "Move Site to Bench":
			process_move_site_to_bench_job_update(job)
		elif job.job_type == "Patch App":
			AppPatch.process_patch_app(job)
		elif job.job_type == "Docker Image Build":
			process_docker_image_build_job_update(job)

	except Exception as e:
		log_error(
			"Agent Job Callback Exception",
			job=job.as_dict(),
			reference_doctype="Agent Job",
			reference_name=job_name,
		)
		raise e


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
			(agent_job.status.isin(["Failure", "Delivery Failure"]))
			& (agent_job_step.status == "Pending")
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
