# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from press.agent import Agent
from press.utils.dns import _change_dns_record


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
				"vxlan_id": self.vxlan_id,
				"subnet_cidr_block": self.subnet_cidr_block,
				"peers": self.get_peers(),
				"network": self.stack,
			}
		)
		self.config = json.dumps(config, indent=4)

	@frappe.whitelist()
	def deploy(self):
		self.agent.new_container(self)
		if self.get_ports():
			domain = frappe.db.get_value("Press Settings", "Press Settings", ["domain"])
			site = frappe.db.get_value("Stack", self.stack, "title")
			_change_dns_record(
				"UPSERT", frappe.get_doc("Root Domain", domain), self.node, record_name=site
			)

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
		containers_on_other_nodes = frappe.get_all(
			"Deployment Container",
			["ip_address", "mac_address", "node", "service"],
			{"parent": self.deployment, "node": ("!=", self.node)},
		)
		peers = []
		for container in containers_on_other_nodes:
			peer = container.copy()
			peer["node_ip_address"] = frappe.db.get_value("Node", peer["node"], "private_ip")
			peer["name"] = frappe.db.get_value("Service", peer["service"], "title")
			peer.pop("Node", None)
			peer.pop("service", None)
			peers.append(peer)

		return peers

	def on_trash(self):
		jobs = frappe.get_all("Agent Job", filters={"container": self.name})
		for job in jobs:
			frappe.get_doc("Agent Job", job.name).delete()


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
