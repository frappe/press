from contextlib import suppress
from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.virtual_machine_image.virtual_machine_image import VirtualMachineImage


class CreateServerSnapshotJob(PressJob):
	@flow
	def execute(self):
		self.stop_virtual_machine()
		self.wait_for_virtual_machine_to_stop()
		self.create_snapshot()
		self.start_virtual_machine()
		self.wait_for_virtual_machine_to_start()
		self.wait_for_snapshot_complete()

	@task
	def stop_virtual_machine(self):
		machine = self.virtual_machine_doc
		with suppress(Exception):
			machine.sync()

			if machine.status == "Stopped":
				return

		machine.stop()

	@task
	def wait_for_virtual_machine_to_stop(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Stopped":
			return

		self.defer_current_task()

	@task
	def create_snapshot(self):
		machine = self.virtual_machine_doc
		self.kv.set("image", machine.create_image())

	@task
	def start_virtual_machine(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

			if self.virtual_machine_doc.status == "Running":
				return

		try:
			self.virtual_machine_doc.start()
		except Exception:
			self.defer_current_task()

	@task
	def wait_for_virtual_machine_to_start(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Running":
			return

		self.defer_current_task()

	@task
	def wait_for_snapshot_complete(self):
		image_name = self.kv.get("image")
		image: VirtualMachineImage = frappe.get_doc("Virtual Machine Image", image_name)  # type: ignore
		image.sync()
		if image.status == "Available":
			return

		self.defer_current_task()
