from contextlib import suppress

import frappe
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.press_job.press_job import STUCK_JOB_MINUTES, PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


def force_fail_stuck_job(job_name: str) -> None:
	workflow_names = frappe.get_all(
		"Press Workflow",
		filters={
			"linked_doctype": "Press Job",
			"linked_docname": job_name,
			"status": ("in", ["Queued", "Running"]),
		},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)

	if workflow_names:
		workflow = frappe.get_doc("Press Workflow", workflow_names[0])
		# The workflow may have completed between the query and this call.
		# In that case there is nothing left to cancel.
		with suppress(frappe.ValidationError):
			workflow.force_fail()


class ArchiveServerJob(PressJob):
	@flow
	def execute(self):
		self.wait_for_active_jobs()
		self.disable_termination_protection()
		self.terminate_virtual_machine()
		self.wait_for_virtual_machine_to_terminate()

	@task
	def wait_for_active_jobs(self):
		active_jobs = frappe.get_all(
			"Press Job",
			filters={
				"status": ("in", ["Pending", "Running"]),
				"server_type": self.server_type,
				"server": self.server,
				"name": ("!=", self.name),
			},
			fields=["name", "creation"],
		)
		if not active_jobs:
			return

		cutoff = add_to_date(now_datetime(), minutes=-STUCK_JOB_MINUTES)
		for job in active_jobs:
			if job.creation < cutoff:
				force_fail_stuck_job(job.name)

		self.defer_current_task()

	@task
	def disable_termination_protection(self):
		if not self.virtual_machine_doc.instance_id:
			return

		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Terminated":
			return

		self.virtual_machine_doc.disable_termination_protection()

	@task(queue="long", timeout=600)
	def terminate_virtual_machine(self):
		if not self.virtual_machine_doc.instance_id:
			# VM was never provisioned on the cloud provider
			# mark it terminated directly
			self.virtual_machine_doc.status = "Terminated"
			self.virtual_machine_doc.save()
			self.virtual_machine_doc.update_servers()
			return

		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Terminated":
			return

		self.virtual_machine_doc.terminate(reason=self.arguments_dict.get("reason", None))

	@task
	def wait_for_virtual_machine_to_terminate(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Terminated":
			self.virtual_machine_doc.update_servers()
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
