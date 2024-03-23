# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

RULE_REACTION_METHOD_MAP = {
	"Disk Full": "increase_disk_size",
}


class PrometheusAlertReaction(Document):
	def validate(self):
		if not self.method_name:
			self.set_method_name_from_map()

	def set_method_name_from_map(self):
		self.method_name = RULE_REACTION_METHOD_MAP[self.rule]

	def after_insert(self):
		self.start()

	def start(self):
		method = getattr(self, self.method_name)
		method(self.instance_type, self.instance)

	def increase_disk_size(self):
		pass
