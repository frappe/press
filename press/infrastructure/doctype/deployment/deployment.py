# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import ipaddress


class Deployment(Document):
	def before_insert(self):
		active_nodes = frappe.get_all("Node", filters={"status": "Active"}, pluck="name")
		stack = frappe.get_doc("Stack", self.stack)
		for index, service in enumerate(stack.services):
			node = active_nodes[index % len(active_nodes)]
			pod = frappe.new_doc("Pod")
			pod.stack = self.stack
			pod.service = service.service
			pod.node = node

			subnet_cidr_block = "10.0.0.0/8"
			network_address = ipaddress.IPv4Interface(subnet_cidr_block).ip

			# Start addresses from .2
			pod.ip_address = str(network_address + index + 2)
			decimals = pod.ip_address.split(".")
			hexes = [f"{int(d):02x}" for d in decimals]

			# This is the same mac address that docker uses for containers
			pod.mac_address = "02:42:" + ":".join(hexes)

			pod.insert()
			self.append("pods", {"node": node, "service": service.service, "pod": pod.name})
