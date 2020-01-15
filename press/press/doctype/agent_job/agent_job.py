# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.press.doctype.bench.bench import Agent
from frappe.core.utils import find
import json


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
				}
			)
			doc.insert()


def poll_pending_jobs():
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "server", "server_type", "job_id"],
		filters={"status": ("in", ["Pending", "Running"])},
	)
	for job in jobs:
		agent = Agent(job.server, server_type=job.server_type)
		polled = agent.get_job_status(job.job_id)

		# Update Job Status
		# If it is worthy of an update
		if job.status != polled["status"]:
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
