# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import ipaddress


class Deployment(Document):
	def before_insert(self):
		active_nodes = frappe.get_all("Node", filters={"status": "Active"}, pluck="name")
		stack = frappe.get_doc("Stack", self.stack)
		for index, stack_service in enumerate(stack.services):
			node = active_nodes[index % len(active_nodes)]
			container = frappe.new_doc("Container")
			container.stack = self.stack
			container.service = stack_service.service
			container.node = node

			subnet_cidr_block = "10.0.0.0/8"
			network_address = ipaddress.IPv4Interface(subnet_cidr_block).ip

			# Start addresses from .2
			container.ip_address = str(network_address + index + 2)
			decimals = container.ip_address.split(".")
			hexes = [f"{int(d):02x}" for d in decimals]

			# This is the same mac address that docker uses for containers
			container.mac_address = "02:42:" + ":".join(hexes)

			container.insert()

			##
			service = frappe.get_doc("Service", container.service)
			for row in service.ports:
				container.append(
					"ports",
					{
						"host_ip": "",
						"host_port": "",
						"container_port": row.port,
						"protocol": row.protocol,
					},
				)
			for row in service.mounts:
				container.append(
					"mounts",
					{
						"source": row.destination,
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

			container.reload()
			for row in container.mounts:
				row.source = f"/home/frappe/containers/{container.name}/{row.destination}"
			container.save()
			self.append(
				"containers",
				{"node": node, "service": container.service, "container": container.name},
			)
