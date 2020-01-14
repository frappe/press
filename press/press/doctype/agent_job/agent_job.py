# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.press.doctype.bench.bench import Agent
from frappe.core.utils import find


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
		"Agent Job", fields=["name", "server", "job_id"], filters={"status": "Pending"}
	)
	for job in jobs:
		agent = Agent(job.server)
		polled = agent.get_job_status(job.job_id)

		# Update Job Status
		frappe.set_value("Agent Job", job.name, "status", polled["status"])

		# Update Steps' Status
		for step in polled["steps"]:
			agent_job_step = frappe.db.get_all(
				"Agent Job Step",
				fields=["name", "status"],
				filters={"agent_job": job.name, "status": "Pending", "step_name": step["name"]},
			)[0]
			if agent_job_step.status == "Pending":
				if step["status"] != "Pending":
					frappe.db.set_value(
						"Agent Job Step", agent_job_step.name, "status", step["status"]
					)
