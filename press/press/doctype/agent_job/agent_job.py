# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe.model.document import Document
from press.agent import Agent
from press.utils import log_error
from frappe.core.utils import find
from itertools import groupby


class AgentJob(Document):
	def after_insert(self):
		self.create_agent_job_steps()
		self.enqueue_http_request()

	def enqueue_http_request(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "create_http_request", enqueue_after_commit=True
		)

	def create_http_request(self):
		agent = Agent(self.server, server_type=self.server_type)
		data = json.loads(self.request_data)
		self.job_id = agent.request(self.request_method, self.request_path, data)["job"]
		self.save()

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

	def retry(self):
		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"status": "Pending",
				"job_type": self.job_type,
				"server_type": self.server_type,
				"server": self.server,
				"bench": self.bench,
				"site": self.site,
				"upstream": self.upstream,
				"host": self.host,
				"request_path": self.request_path,
				"request_data": self.request_data,
				"request_method": self.request_method,
			}
		).insert()
		return job


def job_detail(job):
	job = frappe.get_doc("Agent Job", job)
	steps = []
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


def collect_site_analytics():
	benches = frappe.get_all(
		"Bench", fields=["name", "server"], filters={"status": "Active"}
	)
	for bench in benches:
		agent = Agent(bench.server)
		logs = agent.fetch_monitor_data(bench.name)
		for log in logs:
			try:
				doc = {
					"name": log["uuid"],
					"site": log["site"],
					"timestamp": log["timestamp"],
					"duration": log["duration"],
				}

				if log["transaction_type"] == "request":
					doc.update(
						{
							"doctype": "Site Request Log",
							"url": log["request"]["path"],
							"ip": log["request"]["ip"],
							"http_method": log["request"]["method"],
							"length": log["request"]["response_length"],
							"status_code": log["request"]["status_code"],
						}
					)
				elif log["transaction_type"] == "job":
					doc.update(
						{
							"doctype": "Site Job Log",
							"job_name": log["job"]["method"],
							"scheduled": log["job"]["scheduled"],
							"wait": log["job"]["wait"],
						}
					)
				frappe.get_doc(doc).insert()
			except frappe.exceptions.DuplicateEntryError:
				log_error("Agent Analytics Collection Exception", log=log, doc=doc)


def collect_site_uptime():
	sites = frappe.get_all(
		"Site",
		fields=["name", "server", "bench"],
		filters={"status": "Active", "enable_uptime_monitoring": True},
	)
	for site in sites:
		try:
			agent = Agent(site.server)
			status = agent.fetch_site_status(site)
			doc = {
				"doctype": "Site Uptime Log",
				"site": site.name,
				"web": status["web"],
				"scheduler": status["scheduler"],
				"timestamp": status["timestamp"],
			}
			frappe.get_doc(doc).insert()
			frappe.db.commit()
		except Exception:
			log_error("Agent Uptime Collection Exception", status=status, doc=doc)


def schedule_backups():
	sites = frappe.get_all(
		"Site",
		fields=["name", "server", "bench"],
		filters={"status": "Active", "enable_scheduled_backups": True},
	)
	for site in sites:
		frappe.get_doc("Site", site.name).backup()


def poll_pending_jobs():
	pending_jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "server", "server_type", "job_id", "status"],
		filters={"status": ("in", ["Pending", "Running"]), "job_id": ("!=", 0)},
		order_by="server, job_id",
	)
	for server, server_jobs in groupby(pending_jobs, lambda x: x.server):
		server_jobs = list(server_jobs)
		agent = Agent(server_jobs[0].server, server_type=server_jobs[0].server_type)
		pending_ids = [j.job_id for j in server_jobs]
		polled_jobs = agent.get_jobs_status(pending_ids)
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
				if polled_job["steps"][-1]["status"] == "Failure":
					skip_pending_steps(job.name)

				process_job_updates(job.name)
			except Exception:
				log_error("Agent Job Poll Exception", job=job, polled=polled_job)
		frappe.db.commit()


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
		from press.press.doctype.server.server import process_new_server_job_update
		from press.press.doctype.bench.bench import (
			process_new_bench_job_update,
			process_archive_bench_job_update,
		)
		from press.press.doctype.site.site import (
			process_new_site_job_update,
			process_archive_site_job_update,
		)
		from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
		from press.press.doctype.site_domain.site_domain import process_new_host_job_update
		from press.press.doctype.site_update.site_update import (
			process_update_site_job_update,
			process_update_site_recover_job_update,
		)

		if job.job_type == "Add Upstream to Proxy":
			process_new_server_job_update(job)
		if job.job_type == "New Bench":
			process_new_bench_job_update(job)
		if job.job_type == "Archive Bench":
			process_archive_bench_job_update(job)
		if job.job_type == "New Site":
			process_new_site_job_update(job)
		if job.job_type == "Add Site to Upstream":
			process_new_site_job_update(job)
		if job.job_type == "Backup Site":
			process_backup_site_job_update(job)
		if job.job_type == "Archive Site":
			process_archive_site_job_update(job)
		if job.job_type == "Remove Site from Upstream":
			process_archive_site_job_update(job)
		if job.job_type == "Add Host to Proxy":
			process_new_host_job_update(job)
		if job.job_type == "Update Site Migrate":
			process_update_site_job_update(job)
		if job.job_type == "Update Site Pull":
			process_update_site_job_update(job)
		if job.job_type == "Recover Failed Site Migration":
			process_update_site_recover_job_update(job)
	except Exception:
		log_error("Agent Job Callback Exception", job=job.as_dict())
