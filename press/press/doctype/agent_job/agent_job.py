# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe.model.document import Document
from press.agent import Agent


class AgentJob(Document):
	def after_insert(self):
		self.create_agent_job_steps()

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
				"request_path": self.request_path,
				"request_data": self.request_data,
				"request_method": self.request_method,
			}
		).insert()
		agent = Agent(self.server, server_type=self.server_type)
		job_id = agent.post(self.request_path, self.request_data)["job"]
		job.job_id = job_id
		job.save()
		return job.name


def publish_update(job):
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
		current = {"name": job.job_type, "status": job.status, "index": len(steps) + 1}

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

	frappe.publish_realtime(event="agent_job_update", message=message, user=job.owner)

def collect_site_analytics():
	benches = frappe.get_all("Bench", fields=["name", "server"], filters={"status": "Active"})
	for bench in benches:
		agent = Agent(bench.server)
		logs = agent.fetch_monitor_data(bench.name)
		request_logs, job_logs = [], []
		for log in logs:
			try:
				if log["transaction_type"] == "request":
					frappe.get_doc({
						"doctype": "Site Request Log",
						"name": log["uuid"],
						"site": log["site"],
						"timestamp": log["timestamp"],
						"duration": log["duration"],
						"url": log["path"],
						"ip": log["ip"],
						"length": log["length"],
						"http_method": log["method"],
						"status_code": log["status_code"],
						"http_referer": log["headers"].get("Referer"),
						"http_user_agent": log["headers"].get("User-Agent"),
						"http_headers": json.dumps(log["headers"], indent=4, sort_keys=True),
					}).insert()				
				elif log["transaction_type"] == "job":
					frappe.get_doc({
						"doctype": "Site Job Log",
						"name": log["uuid"],
						"site": log["site"],
						"job_name": log["method"],
						"timestamp": log["timestamp"],
						"duration": log["duration"],
					}).insert()
			except frappe.exceptions.DuplicateEntryError:
				pass


def collect_site_uptime():
	sites = frappe.get_all("Site", fields=["name", "server", "bench"], filters={"status": "Active", "enable_uptime_monitoring": True})
	for site in sites:
		try:
			agent = Agent(site.server)
			status = agent.fetch_site_status(site)
			frappe.get_doc({
				"doctype": "Site Uptime Log",
				"site": site.name,
				"web": status["web"],
				"scheduler": status["scheduler"],
				"timestamp": status["timestamp"],
			}).insert()
			frappe.db.commit()
		except Exception:
			pass


def poll_pending_jobs():
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "server", "server_type", "job_id"],
		filters={"status": ("in", ["Pending", "Running"])},
	)
	for job in jobs:

		if not job.job_id:
			continue

		agent = Agent(job.server, server_type=job.server_type)
		polled = agent.get_job_status(job.job_id)

		# Update Job Status
		# If it is worthy of an update
		if job.status != polled["status"]:
			frappe.db.set_value("Agent Job", job.name, "start", polled["start"])
			frappe.db.set_value("Agent Job", job.name, "end", polled["end"])
			frappe.db.set_value("Agent Job", job.name, "duration", polled["duration"])

			frappe.db.set_value("Agent Job", job.name, "status", polled["status"])
			frappe.db.set_value(
				"Agent Job", job.name, "data", json.dumps(polled["data"], indent=4, sort_keys=True)
			)
			frappe.db.set_value("Agent Job", job.name, "output", polled["data"].get("output"))
			frappe.db.set_value(
				"Agent Job", job.name, "traceback", polled["data"].get("traceback")
			)

		# Update Steps' Status
		for step in polled["steps"]:
			agent_job_step = frappe.db.get_all(
				"Agent Job Step",
				fields=["name", "status"],
				filters={
					"agent_job": job.name,
					"status": ("in", ["Pending", "Running"]),
					"step_name": step["name"],
				},
			)
			if agent_job_step:
				agent_job_step = agent_job_step[0]
				if agent_job_step.status != step["status"]:
					frappe.db.set_value("Agent Job Step", agent_job_step.name, "start", step["start"])
					frappe.db.set_value("Agent Job Step", agent_job_step.name, "end", step["end"])
					frappe.db.set_value(
						"Agent Job Step", agent_job_step.name, "duration", step["duration"]
					)

					frappe.db.set_value(
						"Agent Job Step", agent_job_step.name, "status", step["status"]
					)
					frappe.db.set_value(
						"Agent Job Step",
						agent_job_step.name,
						"data",
						json.dumps(step["data"], indent=4, sort_keys=True),
					)
					frappe.db.set_value(
						"Agent Job Step", agent_job_step.name, "output", step["data"].get("output")
					)
					frappe.db.set_value(
						"Agent Job Step", agent_job_step.name, "traceback", step["data"].get("traceback")
					)
		publish_update(job.name)

		if step["status"] == "Failure":
			frappe.db.sql(
				"UPDATE `tabAgent Job Step` SET status = 'Skipped' WHERE status = 'Pending' AND agent_job = %s",
				job.name,
			)

		job = frappe.get_doc("Agent Job", job.name)
		process_job_updates(job)


def process_job_updates(job):
	from press.press.doctype.bench.bench import process_new_bench_job_update
	from press.press.doctype.bench_deploy.bench_deploy import (
		process_bench_deploy_job_update,
	)
	from press.press.doctype.site.site import (
		process_new_site_job_update,
		process_archive_site_job_update,
	)
	from press.press.doctype.site_backup.site_backup import process_backup_site_job_update

	if job.job_type == "New Bench":
		process_new_bench_job_update(job)
		process_bench_deploy_job_update(job)
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
