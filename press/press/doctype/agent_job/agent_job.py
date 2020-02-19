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
					"duration": "00:00:00"
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

		if step["status"] == "Failure":
			frappe.db.sql("UPDATE `tabAgent Job Step` SET status = 'Skipped' WHERE status = 'Pending' AND agent_job = %s", job.name)
			
		job = frappe.get_doc("Agent Job", job.name)
		process_job_updates(job)


def process_job_updates(job):
	from press.press.doctype.bench.bench import process_new_bench_job_update
	from press.press.doctype.bench_deploy.bench_deploy import (
		process_bench_deploy_job_update,
	)
	from press.press.doctype.site.site import process_new_site_job_update
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
