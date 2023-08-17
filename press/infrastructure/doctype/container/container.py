# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from press.agent import Agent


class Container(Document):
	def validate(self):
		config = json.loads(self.config)
		config.update(
			{
				"image": self.image,
				"environment_variables": self.get_environment_variables(),
				"ports": self.get_ports(),
				"mounts": self.get_mounts(),
			}
		)
		self.config = json.dumps(config, indent=4)

	@frappe.whitelist()
	def deploy(self):
		self.agent.new_container(self)

	@frappe.whitelist()
	def archive(self):
		self.agent.archive_container(self)

	@property
	def agent(self):
		return Agent(self.node, "Node")

	def get_environment_variables(self):
		return {v.key: v.value for v in self.environment_variables}

	def get_mounts(self):
		return [
			{
				"source": mount.source,
				"destination": mount.destination,
				"options": mount.options,
			}
			for mount in self.mounts
		]

	def get_ports(self):
		return [
			{
				"host_ip": port.host_ip,
				"host_port": port.host_port,
				"container_port": port.container_port,
				"protocol": port.protocol,
			}
			for port in self.ports
		]


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
