# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressJob(Document):
	def after_insert(self):
		self.create_press_job_steps()
		self.start()

	def create_press_job_steps(self):
		job_type = frappe.get_doc("Press Job Type", self.job_type)
		for step in job_type.steps:
			doc = frappe.get_doc(
				{
					"doctype": "Press Job Step",
					"job": self.name,
					"status": "Pending",
					"job_type": self.job_type,
					"step_name": step.step_name,
					"wait_until_true": step.wait_until_true,
					"duration": "00:00:00",
				}
			)
			doc.insert()

	def start(self):
		self.status = "Running"
		self.next()

	def succeed(self):
		self.status = "Success"
		self.save()

	@frappe.whitelist()
	def next(self):
		next_step = self.next_step

		if not next_step:
			self.succeed()
			return

		frappe.get_doc("Press Job Step", next_step).execute()

	@property
	def next_step(self):
		return frappe.db.get_value(
			"Press Job Step",
			{"job": self.name, "status": "Pending"},
			"name",
			order_by="name asc",
			as_dict=True,
		)
