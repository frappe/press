from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.server_snapshot.server_snapshot import ServerSnapshot


class SnapshotDiskJob(PressJob):
	@flow
	def execute(self):
		self.verify_virtual_machine_status()

		if self.is_consistent_snapshot:
			if self.server_type == "Server":
				self.stop_docker_daemon()
			if self.server_type == "Database Server":
				self.stop_mariadb_service()

		self.flush_file_system_buffers()
		self.snapshot_disk()

	@property
	def is_consistent_snapshot(self):
		return self.arguments_dict.get("is_consistent_snapshot", False)

	@task
	def verify_virtual_machine_status(self):
		try:
			self.virtual_machine_doc.sync()
		except Exception:
			self.defer_current_task()

		if self.virtual_machine_doc.status == "Terminated":
			raise Exception("Can't snapshot terminated virtual machine")

		if self.virtual_machine_doc.status == "Draft":
			raise Exception("Can't snapshot draft virtual machine")

	@task
	def stop_docker_daemon(self):
		if not (self.server_type == "Server" and self.is_consistent_snapshot):
			return

		output = self.server_doc.ansible_run("systemctl stop docker")
		if not (output and output.get("status") == "Success"):
			raise Exception("Failed to stop docker daemon")

	@task
	def stop_mariadb_service(self):
		if not (self.server_type == "Database Server" and self.is_consistent_snapshot):
			return

		output = self.server_doc.ansible_run("systemctl stop mariadb")
		if not (output and output.get("status") == "Success"):
			raise Exception("Failed to stop mariadb service")

	@task
	def flush_file_system_buffers(self):
		output = self.server_doc.ansible_run("sync")
		if not (output and output.get("status") == "Success"):
			raise Exception("Failed to flush file system buffers to disk")

	@task
	def snapshot_disk(self):
		machine = self.virtual_machine_doc
		machine.create_snapshots(exclude_boot_volume=True, dedicated_snapshot=True)

		field_name = "app_server_snapshot" if self.server_type == "Server" else "database_server_snapshot"
		no_of_snapshots = len(machine.flags.created_snapshots)
		if no_of_snapshots != 1:
			raise Exception(f"Expected 1 disk snapshot. Found: {no_of_snapshots}")

		frappe.db.set_value(
			"Server Snapshot",
			self.arguments_dict.get("server_snapshot"),
			field_name,
			machine.flags.created_snapshots[0],
			update_modified=False,
		)

	def _resume_services(self) -> ServerSnapshot:
		snapshot = frappe.get_doc("Server Snapshot", self.arguments_dict.get("server_snapshot"))
		if self.server_type == "Server":
			snapshot.resume_app_server_services()
		elif self.server_type == "Database Server":
			snapshot.resume_database_server_services()

		return snapshot

	def on_press_job_success(self, workflow):
		snapshot = self._resume_services()
		snapshot.sync(now=False)

	def on_press_job_failure(self, workflow):
		snapshot = self._resume_services()
		frappe.db.set_value("Server Snapshot", snapshot.name, "status", "Failure", update_modified=False)
		for s in snapshot.snapshots:
			with suppress(Exception):
				frappe.get_doc("Virtual Disk Snapshot", s).delete_snapshot(ignore_validation=True)
