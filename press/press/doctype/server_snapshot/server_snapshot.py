# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json
from typing import Literal

import frappe
from frappe.model.document import Document


class ServerSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app_server: DF.Link
		app_server_resume_service_press_job: DF.Link | None
		app_server_services_started: DF.Check
		app_server_snapshot: DF.Link | None
		app_server_snapshot_press_job: DF.Link | None
		cluster: DF.Link
		consistent: DF.Check
		database_server: DF.Link
		database_server_resume_service_press_job: DF.Link | None
		database_server_services_started: DF.Check
		database_server_snapshot: DF.Link | None
		database_server_snapshot_press_job: DF.Link | None
		locked: DF.Check
		provider: DF.Literal["AWS EC2", "OCI"]
		status: DF.Literal["Pending", "Failure", "Completed", "Unavailable"]
		team: DF.Link
	# end: auto-generated types

	@property
	def snapshots(self):
		snapshots = []
		if self.app_server_snapshot:
			snapshots.append(self.app_server_snapshot)
		if self.database_server_snapshot:
			snapshots.append(self.database_server_snapshot)
		return snapshots

	@property
	def arguments_for_press_job(self):
		return {
			"server_snapshot": self.name,
			"is_consistent_snapshot": self.consistent,
		}

	def validate(self):
		if self.provider != "AWS EC2":
			frappe.throw("Only AWS Provider is supported for now")

	def before_insert(self):
		# Ensure both the server and database server isn't archived
		allowed_statuses = ["Pending", "Running", "Stopped"]
		if (
			frappe.db.get_value(
				"Virtual Machine", frappe.db.get_value("Server", self.app_server, "virtual_machine"), "status"
			)
			not in allowed_statuses
		):
			frappe.throw(
				"App Server should be in a valid state [Pending, Running, Stopped] to create a snapshot"
			)
		if (
			frappe.db.get_value(
				"Virtual Machine",
				frappe.db.get_value("Database Server", self.database_server, "virtual_machine"),
				"status",
			)
			not in allowed_statuses
		):
			frappe.throw(
				"Database Server should be in a valid state [Pending, Running, Stopped] to create a snapshot"
			)

	def after_insert(self):
		self.create_press_jobs()

	@frappe.whitelist()
	def create_press_jobs(self):
		self.app_server_snapshot_press_job = frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": "Snapshot Disk",
				"server_type": "Server",
				"server": self.app_server,
				"virtual_machine": frappe.db.get_value("Server", self.app_server, "virtual_machine"),
				"arguments": json.dumps(self.arguments_for_press_job, indent=2, sort_keys=True),
			}
		).insert(ignore_permissions=True)
		self.database_server_snapshot_press_job = frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": "Snapshot Disk",
				"server_type": "Database Server",
				"server": self.database_server,
				"virtual_machine": frappe.db.get_value(
					"Database Server", self.database_server, "virtual_machine"
				),
				"arguments": json.dumps(self.arguments_for_press_job, indent=2, sort_keys=True),
			}
		).insert(ignore_permissions=True)
		self.save(ignore_version=True)

	def resume_app_server_services(self):
		if self.app_server_services_started:
			return
		self.resume_services("Server")

	def resume_database_server_services(self):
		if self.database_server_services_started:
			return
		self.resume_services("Database Server")

	def resume_services(self, server_type: Literal["Server", "Database Server"]):
		if (server_type == "Server" and self.app_server_services_started) or (
			server_type == "Database Server" and self.database_server_services_started
		):
			return

		if not self.consistent:
			frappe.db.set_value(
				self.doctype,
				self.name,
				"app_server_services_started"
				if server_type == "Server"
				else "database_server_services_started",
				True,
				update_modified=True,
			)
			return

		frappe.db.get_value(self.doctype, self.name, "status", for_update=True)

		press_job = frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": "Resume Services After Snapshot",
				"server_type": server_type,
				"server": self.app_server if server_type == "Server" else self.database_server,
				"virtual_machine": frappe.db.get_value(
					"Server" if server_type == "Server" else "Database Server",
					self.app_server if server_type == "Server" else self.database_server,
					"virtual_machine",
				),
				"arguments": json.dumps(self.arguments_for_press_job, indent=2, sort_keys=True),
			}
		).insert(ignore_permissions=True)

		frappe.db.set_value(
			"Server Snapshot",
			self.name,
			"app_server_resume_service_press_job"
			if server_type == "Server"
			else "database_server_resume_service_press_job",
			press_job.name,
			update_modified=False,
		)

	@frappe.whitelist()
	def sync(self, now: bool = False):
		frappe.enqueue_doc(
			"Server Snapshot",
			self.name,
			"_sync",
			enqueue_after_commit=True,
			now=now or False,
		)

	def _sync(self):
		if self.status not in ["Pending", "Completed"]:
			# If snapshot is already marked as failure or unavailable, no need to sync
			return

		updated_status = self.status
		if len(self.snapshots) == 2:
			completed = True
			for s in self.snapshots:
				snapshot_status = frappe.get_value("Virtual Disk Snapshot", s, "status")
				if snapshot_status == "Unavailable":
					updated_status = "Unavailable"
					break
				if snapshot_status != "Completed":
					# If snapshot is not completed, enqueue the sync
					frappe.enqueue_doc(
						"Virtual Disk Snapshot",
						s,
						"sync",
						enqueue_after_commit=True,
					)
					completed = False
					break

			if completed:
				updated_status = "Completed"

		if self.status != updated_status:
			self.status = updated_status
			self.save(ignore_version=True)

	@frappe.whitelist()
	def delete_snapshots(self):
		if self.status in ["Unavailable", "Failure"]:
			# If snapshot is already marked as failure or unavailable, no need to delete
			return

		if self.locked:
			frappe.throw("Snapshot is locked. Unlock the snapshot before deleting.")

		for s in self.snapshots:
			try:
				frappe.get_doc("Virtual Disk Snapshot", s).delete_snapshot()
			except frappe.exceptions.TimestampMismatchError:
				# sync method of disk snapshot can raise version mismatch error
				pass
			except Exception as e:
				raise e

		self.status = "Unavailable"
		self.save()

	@frappe.whitelist()
	def lock(self, now: bool = False):
		if self.locked:
			return

		frappe.enqueue_doc("Server Snapshot", self.name, "_lock", enqueue_after_commit=True, now=now or False)

	@frappe.whitelist()
	def unlock(self, now: bool = False):
		if not self.locked:
			return

		frappe.enqueue_doc(
			"Server Snapshot",
			self.name,
			"_unlock",
			enqueue_after_commit=True,
			now=now or False,
		)

	def _lock(self):
		for s in self.snapshots:
			frappe.get_doc("Virtual Disk Snapshot", s).lock()
		self.locked = True
		self.save(ignore_version=True)

	def _unlock(self):
		for s in self.snapshots:
			frappe.get_doc("Virtual Disk Snapshot", s).unlock()
		self.locked = False
		self.save(ignore_version=True)
