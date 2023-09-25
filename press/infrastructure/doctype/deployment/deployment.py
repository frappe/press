# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import ipaddress
import random


class Deployment(Document):
	def before_insert(self):
		active_nodes = frappe.get_all("Node", filters={"status": "Active"}, pluck="name")
		stack = frappe.get_doc("Stack", self.stack)
		for index, service in enumerate(stack.services):
			service = frappe.get_doc("Service", service.service)
			node = active_nodes[index % len(active_nodes)]
			network_address = ipaddress.IPv4Interface(stack.subnet_cidr_block).ip
			# Start addresses from .2
			ip_address = str(network_address + index + 2)
			decimals = ip_address.split(".")
			hexes = [f"{int(d):02x}" for d in decimals]
			# This is the same mac address that docker uses for containers
			mac_address = "02:42:" + ":".join(hexes)
			self.append(
				"containers",
				{
					"node": node,
					"service": service.name,
					"image": f"{service.image}:{service.tag}",
					"ip_address": ip_address,
					"mac_address": mac_address,
				},
			)

	def after_insert(self):
		for deployment_container in self.containers:
			container = frappe.new_doc("Container")
			container.deployment = self.name
			container.service = deployment_container.service
			container.image = deployment_container.image
			container.node = deployment_container.node
			container.ip_address = deployment_container.ip_address
			container.mac_address = deployment_container.mac_address

			service = frappe.get_doc("Service", container.service)
			host_ports = self.get_random_port(container.node, len(service.ports))
			for row, host_port in zip(service.ports, host_ports):
				container.append(
					"ports",
					{
						"host_ip": "127.0.0.1",
						"host_port": host_port,
						"container_port": row.port,
						"protocol": row.protocol,
					},
				)
			for row in service.mounts:
				container.append(
					"mounts",
					{
						"source": f"/home/frappe/stacks/{self.stack}/volumes/{row.volume}/{row.source}",
						"destination": row.destination,
						"options": row.options,
					},
				)

			for row in service.environment_variables:
				if row.required:
					container.append(
						"environment_variables",
						{
							"key": row.key,
							"value": row.default_value,
						},
					)

			container.insert()
			container.deploy()

	def get_random_port(self, node, count):
		rows = frappe.db.sql(
			"""
		SELECT host_port FROM `tabContainer Port`
		LEFT JOIN `tabContainer` ON `tabContainer Port`.parent = `tabContainer`.name
		WHERE `tabContainer`.status != "Archived" AND `tabContainer`.node = %s""",
			node,
			as_dict=True,
		)
		port_range = set(range(30000, 60000))
		occupied_ports = set(row.host_port for row in rows)

		return random.sample(list(port_range - occupied_ports), count)

	def update_status(self):
		containers = frappe.get_all("Container", ["name"], {"deployment": self.name})
		statuses = set()
		for container in containers:
			statuses.add(
				frappe.get_all(
					"Agent Job",
					{"container": container.name, "job_type": "New Container"},
					pluck="status",
					limit=1,
				)[0]
			)

		if "Failure" in statuses:
			self.status = "Failure"
		elif "Pending" in statuses and "Running" in statuses:
			self.status = "Running"
		elif "Success" in statuses and len(statuses) == 1:
			self.status = "Success"

		self.save()

	def on_update(self):
		jobs = []
		containers = frappe.get_all(
			"Container", ["name", "service"], {"deployment": self.name}
		)
		for container in containers:
			job = frappe.get_all(
				"Agent Job",
				["name", "status", "start", "end", "duration", "creation", "modified"],
				{"container": container.name, "job_type": "New Container"},
				limit=1,
			)[0]
			job.service = frappe.db.get_value("Service", container.service, "title")
			jobs.append(job)

		if self.status == "Running":
			frappe.publish_realtime(
				f"stack_deploy:{self.name}:jobs", {"jobs": jobs, "name": self.name}
			)
		if self.status == "Success":
			frappe.publish_realtime(f"stack_deploy:{self.name}:finished")

	def on_trash(self):
		containers = frappe.get_all("Container", filters={"deployment": self.name})
		for container in containers:
			frappe.get_doc("Container", container.name).delete()
