# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import contextlib
import json
from typing import TYPE_CHECKING, Literal

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.site_backup.site_backup import VirtualMachine


class ServerSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app_server: DF.Link
		app_server_ram: DF.Int
		app_server_resume_service_press_job: DF.Link | None
		app_server_services_started: DF.Check
		app_server_snapshot: DF.Link | None
		app_server_snapshot_press_job: DF.Link | None
		app_server_vcpu: DF.Int
		cluster: DF.Link
		consistent: DF.Check
		database_server: DF.Link
		database_server_ram: DF.Int
		database_server_resume_service_press_job: DF.Link | None
		database_server_services_started: DF.Check
		database_server_snapshot: DF.Link | None
		database_server_snapshot_press_job: DF.Link | None
		database_server_vcpu: DF.Int
		locked: DF.Check
		provider: DF.Literal["AWS EC2", "OCI"]
		site_list: DF.JSON | None
		status: DF.Literal["Pending", "Failure", "Completed", "Unavailable"]
		team: DF.Link
		total_size_gb: DF.Int
		traceback: DF.Text | None
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
	def sites(self) -> list[str]:
		if not self.site_list:
			return []
		try:
			return json.loads(self.site_list)
		except:  # noqa: E722
			return []

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
		app_server_vm = frappe.db.get_value("Server", self.app_server, "virtual_machine")
		db_server_vm = frappe.db.get_value("Database Server", self.database_server, "virtual_machine")
		if frappe.db.get_value("Virtual Machine", app_server_vm, "status") not in allowed_statuses:
			frappe.throw(
				"App Server should be in a valid state [Pending, Running, Stopped] to create a snapshot"
			)
		if frappe.db.get_value("Virtual Machine", db_server_vm, "status") not in allowed_statuses:
			frappe.throw(
				"Database Server should be in a valid state [Pending, Running, Stopped] to create a snapshot"
			)

		sites = (
			frappe.get_all(
				"Site",
				filters={"server": self.app_server, "status": ("!=", "Archived")},
				pluck="name",
			)
			or []
		)
		self.site_list = json.dumps(sites, indent=2, sort_keys=True)

		# Ensure no other snapshot is in Pending state
		if frappe.db.exists(
			"Server Snapshot",
			{
				"status": "Pending",
				"app_server": self.app_server,
				"database_server": self.database_server,
			},
		):
			frappe.throw(
				f"A snapshot for App Server {self.app_server} and Database Server {self.database_server} is already in Pending state."
			)

		# Set vCPU and RAM configuration
		vm: VirtualMachine = frappe.get_doc("Virtual Machine", app_server_vm)
		self.app_server_vcpu = vm.vcpu
		self.app_server_ram = vm.ram

		vm: VirtualMachine = frappe.get_doc("Virtual Machine", db_server_vm)
		self.database_server_vcpu = vm.vcpu
		self.database_server_ram = vm.ram

	def after_insert(self):
		try:
			self.create_press_jobs()
		except Exception:
			import traceback

			self.traceback = traceback.format_exc()
			self.status = "Failure"
			self.save(ignore_version=True)

			# Clear created press jobs (if any)
			if (
				hasattr(self, "flags")
				and hasattr(self.flags, "created_press_jobs")
				and isinstance(self.flags.created_press_jobs, list)
			):
				for job in self.flags.created_press_jobs:
					with contextlib.suppress(Exception):
						frappe.get_doc("Press Job", job).delete(ignore_permissions=True)

	def create_press_jobs(self):
		self.flags.created_press_jobs = []
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
		self.flags.created_press_jobs.append(self.app_server_snapshot_press_job.name)
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
		self.flags.created_press_jobs.append(self.database_server_snapshot_press_job.name)
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
	def sync(self, now: bool | None = None, trigger_snapshot_sync: bool | None = None):
		if now is None:
			now = False

		if trigger_snapshot_sync is None:
			trigger_snapshot_sync = True

		frappe.enqueue_doc(
			"Server Snapshot",
			self.name,
			"_sync",
			enqueue_after_commit=True,
			now=now,
			trigger_snapshot_sync=trigger_snapshot_sync,
		)

	def _sync(self, trigger_snapshot_sync):  # noqa: C901
		if self.status not in ["Pending", "Completed"]:
			# If snapshot is already marked as failure or unavailable, no need to sync
			return

		updated_status = self.status
		total_size = 0
		if len(self.snapshots) == 2:
			completed = True
			for s in self.snapshots:
				snapshot_info = frappe.get_value("Virtual Disk Snapshot", s, ["status", "size"], as_dict=True)
				if snapshot_info["status"] == "Unavailable":
					updated_status = "Unavailable"
					break
				if snapshot_info["status"] != "Completed":
					if trigger_snapshot_sync:
						# If snapshot is not completed, enqueue the sync
						frappe.enqueue_doc(
							"Virtual Disk Snapshot",
							s,
							"sync",
							enqueue_after_commit=True,
						)
					completed = False
					break

				total_size += snapshot_info["size"]

			if completed:
				updated_status = "Completed"

		if self.status != updated_status or self.total_size_gb != total_size:
			self.status = updated_status
			self.total_size_gb = total_size
			self.save(ignore_version=True)

	@frappe.whitelist()
	def delete_snapshots(self):
		if self.status in ["Unavailable", "Failure"]:
			# If snapshot is already marked as failure or unavailable, no need to delete
			return

		if self.locked:
			frappe.throw("Snapshot is locked. Unlock the snapshot before deleting.")

		for s in self.snapshots:
			frappe.enqueue_doc(
				"Virtual Disk Snapshot",
				s,
				"delete_snapshot",
				enqueue_after_commit=True,
				ignore_validation=True,
			)

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
