# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from press.agent import Agent


class Container(Document):
	def validate(self):
		config = json.loads(self.config)
		self.config = json.dumps(config, indent=4)
		config.update(
			{
				"image": self.image,
			}
		)
		self.config = json.dumps(config, indent=4)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.node, "Node")
		agent.new_container(self)


def process_new_container_job_update(job):
	container = frappe.get_doc("Container", job.container)

	updated_status = {
		"Pending": "Pending",
		"Running": "Installing",
		"Success": "Active",
		"Failure": "Broken",
	}[job.status]

	if updated_status != container.status:
		frappe.db.set_value("Container", job.container, "status", updated_status)


def process_archive_container_job_update(job):
	container_status = frappe.get_value("Container", job.container, "status")

	updated_status = {
		"Pending": "Pending",
		"Running": "Pending",
		"Success": "Archived",
		"Failure": "Broken",
	}[job.status]

	if updated_status != container_status:
		frappe.db.set_value("Container", job.container, "status", updated_status)
