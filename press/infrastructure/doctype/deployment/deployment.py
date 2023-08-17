# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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
			pod.insert()
			self.append("pods", {"node": node, "service": service.service, "pod": pod.name})
