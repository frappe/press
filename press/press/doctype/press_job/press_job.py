# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressJob(Document):
	def after_insert(self):
		self.create_press_job_steps()
		self.execute()

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

	def execute(self):
		self.status = "Running"
		self.start = frappe.utils.now_datetime()
		self.save()
		self.next()

	def fail(self):
		self.status = "Failure"
		pending_steps = frappe.get_all(
			"Press Job Step", {"job": self.name, "status": "Pending"}
		)
		for step in pending_steps:
			frappe.db.set_value("Press Job Step", step.name, "status", "Skipped")
		self.end = frappe.utils.now_datetime()
		self.duration = self.end - self.start
		self.save()

	def succeed(self):
		self.status = "Success"
		self.end = frappe.utils.now_datetime()
		self.duration = self.end - self.start
		self.save()

	@frappe.whitelist()
	def next(self):
		self.status = "Running"
		self.save()
		next_step = self.next_step

		if not next_step:
			self.succeed()
			return

		frappe.enqueue_doc("Press Job Step", next_step, "execute")

	@property
	def next_step(self):
		return frappe.db.get_value(
			"Press Job Step",
			{"job": self.name, "status": "Pending"},
			"name",
			order_by="name asc",
			as_dict=True,
		)
