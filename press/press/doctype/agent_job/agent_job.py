# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import frappe
import random

from press.agent import Agent
from itertools import groupby
from press.utils import log_error
from frappe.core.utils import find
from frappe.model.document import Document
from press.press.doctype.site_migration.site_migration import (
	get_ongoing_migration,
	process_site_migration_job_update,
)


class AgentJob(Document):
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

			self.job_id = agent.request(self.request_method, self.request_path, data, files)[
				"job"
			]
			self.status = "Pending"
			self.save()
		except Exception:
			self.status = "Failure"
			self.save()
			process_job_updates(self.name)
			frappe.db.set_value(
				"Agent Job", self.name, "status", "Undelivered", for_update=False
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
	def retry_skip_failing_patches(self):
		# Add the skip flag and update request data
		updated_request_data = json.loads(self.request_data) if self.request_data else {}
		updated_request_data["skip_failing_patches"] = True
		self.request_data = json.dumps(updated_request_data, indent=4, sort_keys=True)

		return self.retry()

	def on_trash(self):
		steps = frappe.get_all("Agent Job Step", filters={"agent_job": self.name})
		for step in steps:
			frappe.delete_doc("Agent Job Step", step.name)


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

	for site in active_sites:
		if site.current_database_usage > 100 or site.current_disk_usage > 100:
			frappe.get_doc("Site", site.name).suspend(reason="Site Usage Exceeds Plan limits")


def poll_pending_jobs():
	pending_jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "server", "server_type", "job_id", "status"],
		filters={"status": ("in", ["Pending", "Running"]), "job_id": ("!=", 0)},
		order_by="server, job_id",
		ignore_ifnull=True,
	)
	for server, server_jobs in groupby(pending_jobs, lambda x: x.server):
		server_jobs = list(server_jobs)
		agent = Agent(server_jobs[0].server, server_type=server_jobs[0].server_type)

		pending_ids = [j.job_id for j in server_jobs]
		random_pending_ids = random.choices(pending_ids, k=100)
		polled_jobs = agent.get_jobs_status(random_pending_ids)

		for polled_job in polled_jobs:
			job = find(server_jobs, lambda x: x.job_id == polled_job["id"])
			try:
				# Update Job Status
				# If it is worthy of an update
				if job.status != polled_job["status"]:
					update_job(job.name, polled_job)

				# Update Steps' Status
				update_steps(job.name, polled_job)
				publish_update(job.name)
				if polled_job["status"] in ("Success", "Failure", "Undelivered"):
					skip_pending_steps(job.name)

				process_job_updates(job.name)
				frappe.db.commit()
			except Exception:
				log_error("Agent Job Poll Exception", job=job, polled=polled_job)
				frappe.db.rollback()


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
		for_update=False,
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
		for_update=False,
	)


def skip_pending_steps(job_name):
	frappe.db.sql(
		"""UPDATE  `tabAgent Job Step` SET  status = 'Skipped'
		WHERE status = 'Pending' AND agent_job = %s""",
		job_name,
	)


def process_job_updates(job_name):
	job = frappe.get_doc("Agent Job", job_name)
	try:
		from press.press.doctype.bench.bench import (
			process_archive_bench_job_update,
			process_new_bench_job_update,
			process_add_ssh_user_job_update,
		)
		from press.press.doctype.server.server import process_new_server_job_update
		from press.press.doctype.site.erpnext_site import (
			process_setup_erpnext_site_job_update,
		)
		from press.press.doctype.site.site import (
			process_archive_site_job_update,
			process_install_app_site_job_update,
			process_migrate_site_job_update,
			process_new_site_job_update,
			process_reinstall_site_job_update,
			process_rename_site_job_update,
			process_restore_tables_job_update,
		)
		from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
		from press.press.doctype.site_domain.site_domain import process_new_host_job_update
		from press.press.doctype.site_update.site_update import (
			process_update_site_job_update,
			process_update_site_recover_job_update,
		)

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
		elif job.job_type == "Restore Site":
			process_reinstall_site_job_update(job)
		elif job.job_type == "Reinstall Site":
			process_reinstall_site_job_update(job)
		elif job.job_type == "Migrate Site":
			process_migrate_site_job_update(job)
		elif job.job_type == "Install App on Site":
			process_install_app_site_job_update(job)
		elif job.job_type == "Uninstall App from Site":
			process_install_app_site_job_update(job)
		elif job.job_type == "Add Site to Upstream":
			process_new_site_job_update(job)
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

	except Exception as e:
		log_error("Agent Job Callback Exception", job=job.as_dict())
		raise e
