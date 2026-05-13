from contextlib import suppress

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class ArchiveServerJob(PressJob):
	@flow
	def execute(self):
		self.disable_termination_protection()
		self.terminate_virtual_machine()
		self.wait_for_virtual_machine_to_terminate()

	@task
	def disable_termination_protection(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Terminated":
			return

		self.virtual_machine_doc.disable_termination_protection()

	@task(queue="long", timeout=600)
	def terminate_virtual_machine(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Terminated":
			return

		self.virtual_machine_doc.terminate()

	@task
	def wait_for_virtual_machine_to_terminate(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Terminated":
			return

		self.defer_current_task()

	def on_press_job_success(self, _):
		if self.server_type not in ["Server", "Database Server"]:
			return

		if not self.server_doc.is_for_recovery:
			return

		recovery_record_name = None
		if self.server_type == "Server":
			recovery_record_name = frappe.db.get_value(
				"Server Snapshot Recovery", {"app_server": self.server}, "name"
			)
		elif self.server_type == "Database Server":
			recovery_record_name = frappe.db.get_value(
				"Server Snapshot Recovery", {"database_server": self.server}, "name"
			)

		if not recovery_record_name:
			return

		recovery_record = frappe.get_doc(
			"Server Snapshot Recovery",
			recovery_record_name,
			for_update=True,
		)
		if self.server_type == "Server":
			recovery_record.app_server_archived = True
		else:
			recovery_record.database_server_archived = True
		recovery_record.save()
