# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import frappe
import random

from press.agent import Agent
from press.utils import log_error
from frappe.core.utils import find
from frappe.model.document import Document
from press.press.doctype.site_migration.site_migration import (
	get_ongoing_migration,
	process_site_migration_job_update,
)
from press.press.doctype.press_notification.press_notification import (
	create_new_notification,
)


class AgentJob(Document):
	def get_doc(self):
		whitelisted_fields = [
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
		]
		out = {key: self.get(key) for key in whitelisted_fields}
		out["steps"] = frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": self.name},
			fields=["step_name", "status", "start", "end", "duration", "output"],
			order_by="creation",
		)
		return out

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
			frappe.db.set_value("Agent Job", self.name, "status", "Undelivered")

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
			publish_update(job.name)
			if polled_job["status"] in ("Success", "Failure", "Undelivered"):
				skip_pending_steps(job.name)

			process_job_updates(job.name)
			frappe.db.commit()
		except Exception:
			log_error("Agent Job Poll Exception", job=job, polled=polled_job)
			frappe.db.rollback()


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
	frappe.db.set_value(
		"Agent Job",
		{
			"status": ("in", ["Pending", "Running"]),
			"job_id": ("!=", 0),
			"modified": ("<", frappe.utils.add_days(None, -2)),
		},
		"status",
		"Failure",
	)

	frappe.db.set_value(
		"Agent Job",
		{
			"job_id": 0,
			"modified": ("<", frappe.utils.add_days(None, -2)),
		},
		"status",
		"Undelivered",
	)


def lock_doc_updated_by_job(job_name):
	"""
	Ensure serializability of callback of jobs associated with the same document

	All select queries in this transaction should have for_update True for this to work correctly
	"""
	doc_names = frappe.db.get_values(
		"Agent Job", job_name, ["site", "bench", "server", "server_type"], as_dict=True
	)[
		0
	]  # relies on order of values to be site, bench..
	for field, doc_name in doc_names.items():
		doctype = field.capitalize()
		if field == "server":
			doctype = doc_names["server_type"]
		elif field == "server_type":  # ideally will never happen, but sanity
			return
		if doc_name:
			frappe.db.get_value(doctype, doc_name, "modified", for_update=True)
			return doc_name


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


def process_job_updates(job_name):
	job = frappe.get_doc("Agent Job", job_name)
	try:
		from press.press.doctype.bench.bench import (
			process_archive_bench_job_update,
			process_new_bench_job_update,
			process_add_ssh_user_job_update,
			process_remove_ssh_user_job_update,
		)
		from press.press.doctype.server.server import process_new_server_job_update
		from press.press.doctype.proxy_server.proxy_server import (
			process_update_nginx_job_update,
		)
		from press.press.doctype.site.erpnext_site import (
			process_setup_erpnext_site_job_update,
		)
		from press.press.doctype.site.site import (
			process_archive_site_job_update,
			process_install_app_site_job_update,
			process_uninstall_app_site_job_update,
			process_migrate_site_job_update,
			process_new_site_job_update,
			process_reinstall_site_job_update,
			process_rename_site_job_update,
			process_restore_tables_job_update,
			process_add_proxysql_user_job_update,
			process_remove_proxysql_user_job_update,
			process_move_site_to_bench_job_update,
			process_restore_job_update,
		)
		from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
		from press.press.doctype.site_domain.site_domain import process_new_host_job_update
		from press.press.doctype.site_update.site_update import (
			process_update_site_job_update,
			process_update_site_recover_job_update,
		)
		from press.press.doctype.code_server.code_server import (
			process_new_code_server_job_update,
			process_start_code_server_job_update,
			process_stop_code_server_job_update,
			process_archive_code_server_job_update,
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
			process_restore_job_update(job)
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

	except Exception as e:
		log_error("Agent Job Callback Exception", job=job.as_dict())
		raise e
