# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class PressJob(Document):
	def after_insert(self):
		self.create_press_job_steps()
		self.execute()

	def on_update(self):
		self.publish_update()

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

	def fail(self, arguments=None):
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
	def next(self, arguments=None):
		if arguments:
			old_arguments = json.loads(self.arguments)
			old_arguments.update(arguments)
			self.arguments = json.dumps(old_arguments, indent=2)
		self.status = "Running"
		self.save()
		next_step = self.next_step

		if not next_step:
			self.succeed()
			return

		frappe.enqueue_doc("Press Job Step", next_step, "execute", enqueue_after_commit=True)

	@frappe.whitelist()
	def force_continue(self):
		for step in frappe.get_all(
			"Press Job Step",
			{"job": self.name, "status": ("in", ("Failure", "Skipped"))},
			pluck="name",
		):
			frappe.db.set_value("Press Job Step", step, "status", "Pending")
		self.next()

	@frappe.whitelist()
	def force_fail(self):
		for step in frappe.get_all(
			"Press Job Step",
			{"job": self.name, "status": "Pending"},
			pluck="name",
		):
			frappe.db.set_value("Press Job Step", step, "status", "Failure")
		frappe.db.set_value("Press Job", self.name, "status", "Failure")

	@property
	def next_step(self):
		return frappe.db.get_value(
			"Press Job Step",
			{"job": self.name, "status": "Pending"},
			"name",
			order_by="name asc",
			as_dict=True,
		)

	def detail(self):
		steps = frappe.get_all(
			"Press Job Step",
			filters={"job": self.name},
			fields=["name", "step_name", "status", "start", "end", "duration"],
			order_by="name asc",
		)

		for index, step in enumerate(steps):
			if step.status == "Pending" and index and steps[index - 1].status == "Success":
				step.status = "Running"

		return {
			"name": self.name,
			"job_type": self.job_type,
			"server": self.server,
			"server_type": self.server_type,
			"virtual_machine": self.virtual_machine,
			"status": self.status,
			"steps": steps,
		}

	def publish_update(self):
		frappe.publish_realtime("press_job_update", self.detail())

	def on_trash(self):
		frappe.db.delete("Press Job Step", {"job": self.name})
