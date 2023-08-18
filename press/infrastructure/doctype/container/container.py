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
				"ip_address": self.ip_address,
				"mac_address": self.mac_address,
				"peers": self.get_peers(),
				"network": self.stack,
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

	def get_peers(self):
		pod = frappe.get_all("Pod Container", {"container": self.name}, pluck="parent")[0]
		deployment = frappe.get_all("Deployment Pod", {"pod": pod}, pluck="parent")[0]
		pods_on_other_nodes = frappe.get_all(
			"Deployment Pod", {"parent": deployment, "node": ("!=", self.node)}, pluck="pod"
		)
		peers = []
		for pod in pods_on_other_nodes:
			peer = frappe.get_value(
				"Pod", pod, ["ip_address", "mac_address", "node"], as_dict=True
			)
			peer["node_ip_address"] = frappe.db.get_value("Node", peer.node, "private_ip")
			peers.append(peer)

		return peers


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
		"Running": "Installing",
		"Success": "Archived",
		"Failure": "Broken",
	}[job.status]

	if updated_status != container_status:
		frappe.db.set_value("Container", job.container, "status", updated_status)
