# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressJob(Document):
	def after_insert(self):
		self.create_press_job_steps()

	def create_press_job_steps(self):
		job_type = frappe.get_doc("Press Job Type", self.job_type)
		for step in job_type.steps:
			doc = frappe.get_doc(
				{
					"doctype": "Press Job Step",
					"job": self.name,
					"status": "Pending",
					"step_name": step.step_name,
					"duration": "00:00:00",
				}
			)
			doc.insert()
