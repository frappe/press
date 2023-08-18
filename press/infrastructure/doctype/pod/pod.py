# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Pod(Document):
	def before_insert(self):
		container = frappe.new_doc("Container")
		container.node = self.node
		container.stack = self.stack
		container.service = self.service
		container.ip_address = self.ip_address
		container.mac_address = self.mac_address
		service = frappe.get_doc("Service", self.service)
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

		container.insert()
		container.reload()
		for row in container.mounts:
			row.source = f"/home/frappe/containers/{container.name}/{row.destination}"
		container.save()

		self.append("containers", {"container": container.name})
