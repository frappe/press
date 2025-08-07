# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import contextlib
import json
from typing import TYPE_CHECKING, Literal

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist

if TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster
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
		expire_at: DF.Datetime | None
		free: DF.Check
		locked: DF.Check
		provider: DF.Literal["AWS EC2", "OCI"]
		site_list: DF.JSON | None
		status: DF.Literal["Pending", "Processing", "Failure", "Completed", "Unavailable"]
		team: DF.Link
		total_size_gb: DF.Int
		traceback: DF.Text | None
	# end: auto-generated types

	dashboard_fields = (
		"status",
		"app_server",
		"database_server",
		"cluster",
		"consistent",
		"locked",
		"free",
		"total_size_gb",
		"app_server_snapshot_press_job",
		"database_server_snapshot_press_job",
		"app_server_resume_service_press_job",
		"database_server_resume_service_press_job",
		"creation",
		"expire_at",
	)

	def get_doc(self, doc: "ServerSnapshot"):
		app_server_snapshot = {}
		database_server_snapshot = {}

		if self.status in ["Processing", "Completed"]:
			if self.app_server_snapshot:
				app_server_snapshot = frappe.get_value(
					"Virtual Disk Snapshot",
					self.app_server_snapshot,
					["size", "progress", "status", "start_time"],
					as_dict=True,
				)
				print(app_server_snapshot)
			if self.database_server_snapshot:
				database_server_snapshot = frappe.get_value(
					"Virtual Disk Snapshot",
					self.database_server_snapshot,
					["size", "progress", "status", "start_time"],
					as_dict=True,
				)

		doc.app_server_hostname = (
			frappe.get_value("Server", self.app_server, "hostname") if self.app_server else ""
		)
		doc.app_server_title = frappe.get_value("Server", self.app_server, "title") if self.app_server else ""
		doc.app_server_snapshot_size = app_server_snapshot.get("size", 0)
		doc.app_server_snapshot_progress = int(app_server_snapshot.get("progress", "0%").strip("%"))
		doc.app_server_snapshot_status = app_server_snapshot.get("status", "")
		doc.app_server_snapshot_start_time = app_server_snapshot.get("start_time", None)

		doc.database_server_title = (
			frappe.get_value("Database Server", self.database_server, "title") if self.database_server else ""
		)
		doc.database_server_hostname = (
			frappe.get_value("Database Server", self.database_server, "hostname")
			if self.database_server
			else ""
		)
		doc.database_server_snapshot_size = database_server_snapshot.get("size", 0)
		doc.database_server_snapshot_progress = int(database_server_snapshot.get("progress", "0%").strip("%"))
		doc.database_server_snapshot_status = database_server_snapshot.get("status", "")
		doc.database_server_snapshot_start_time = database_server_snapshot.get("start_time", None)

		doc.progress = int(((doc.app_server_snapshot_progress) + (doc.database_server_snapshot_progress)) / 2)

		doc.site_list_json = self.sites

		return doc

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

	@property
	def subscription(self) -> str | None:
		return frappe.db.get_value(
			"Subscription", {"document_type": "Server Snapshot", "document_name": self.name}
		)

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

	def on_update(self):
		if self.has_value_changed("status"):
			if self.status == "Completed":
				self._create_subscription()
			elif self.status in ["Failure", "Unavailable"]:
				self._disable_subscription()

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
		if self.status not in ["Processing", "Completed"]:
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

	@dashboard_whitelist()
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

	@dashboard_whitelist()
	def lock(self, now: bool = False):
		if self.locked:
			return

		frappe.enqueue_doc("Server Snapshot", self.name, "_lock", enqueue_after_commit=True, now=now or False)

	@dashboard_whitelist()
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

	@dashboard_whitelist()
	def recover_sites(self, sites: list[str] | None = None):
		if not sites:
			sites = []

		recover_record = frappe.get_doc(
			{
				"doctype": "Server Snapshot Recovery",
				"snapshot": self.name,
			}
		)
		for s in sites:
			recover_record.append("sites", {"site": s})
		recover_record.insert(ignore_permissions=True)
		frappe.msgprint(
			"Snapshot Recovery started successfully\n"
			f"<a href='/app/server-snapshot-recovery/{recover_record.name}' target='_blank'>View Recovery Record</a>."
		)
		return recover_record.name

	@frappe.whitelist()
	def create_server(  # noqa: C901
		self,
		server_type: Literal["Server", "Database Server"],
		title: str | None = None,
		plan: str | None = None,
		team: str | None = None,
		create_subscription: bool | None = False,
		database_server: str | None = None,
		temporary_server: bool | None = False,
		is_for_recovery: bool = False,
		provision_db_replica: bool = False,
		master_db_server: str | None = None,
	) -> str:
		if server_type not in ["Server", "Database Server"]:
			frappe.throw("Invalid server type. Must be 'Server' or 'Database Server'.")

		if create_subscription is None:
			create_subscription = False

		if temporary_server is None:
			temporary_server = False

		if provision_db_replica is None:
			provision_db_replica = False

		if server_type != "Database Server" and provision_db_replica:
			frappe.throw("Provisioning a database replica is only applicable for Database Servers.")

		if provision_db_replica and not master_db_server:
			frappe.throw("Master Database Server is required for provisioning a database replica.")

		if temporary_server and provision_db_replica:
			frappe.throw("Temporary server cannot be used for provisioning a database replica.")

		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)
		if not plan:
			plan = cluster.find_server_plan_with_compute_config(
				server_type=server_type,
				vcpu=self.app_server_vcpu if server_type == "Server" else self.database_server_vcpu,
				memory=self.app_server_ram if server_type == "Server" else self.database_server_ram,
			)

		cluster.proxy_server = frappe.get_all(
			"Proxy Server",
			{"status": "Active", "cluster": cluster.name, "is_primary": True},
			pluck="name",
			limit=1,
		)[0]

		if database_server:
			cluster.database_server = database_server

		server, _ = cluster.create_server(
			doctype=server_type,
			title=title or self.name,
			team=team,
			data_disk_snapshot=self.app_server_snapshot
			if server_type == "Server"
			else self.database_server_snapshot,
			plan=frappe.get_doc("Server Plan", plan) if isinstance(plan, str) else plan,
			create_subscription=create_subscription,
			temporary_server=temporary_server,
			is_for_recovery=is_for_recovery,
			setup_db_replication=provision_db_replica,
			master_db_server=master_db_server if provision_db_replica else None,
		)
		server_name = ""
		if server:
			server_name = server.name

		frappe.msgprint(
			f"Server {server_name} created successfully from snapshot\n.<a href='/app/{server_type.lower().replace(' ', '-')}/{server_name}' target='_blank'>{server_name}</a>."
			f" Please check the server for further actions."
		)

		return server_name

	def _create_subscription(self):
		"""
		Create a subscription for the server snapshot.
		This method can be called after the server snapshot is completed.
		"""
		if self.free:
			return

		plan = frappe.get_value("Server Snapshot Plan", {"provider": self.provider, "enabled": 1}, "name")
		if not plan:
			frappe.throw(f"No active Server Snapshot Plan found for provider {self.provider}.")

		frappe.get_doc(
			{
				"doctype": "Subscription",
				"enabled": 1,
				"team": self.team,
				"document_type": "Server Snapshot",
				"document_name": self.name,
				"plan_type": "Server Snapshot Plan",
				"plan": plan,
				"interval": "Daily",
			}
		).insert(ignore_permissions=True)

	def _disable_subscription(self):
		"""
		Delete the subscription for the server snapshot.
		This method can be called when the server snapshot is archived or deleted.
		"""
		frappe.db.set_value(
			"Subscription",
			self.subscription,
			"enabled",
			0,
			update_modified=True,
		)


def move_pending_snapshots_to_processing():
	"""
	Move all pending snapshots to processing state.
	This is used to ensure that snapshots are processed in the correct order.
	"""
	pending_snapshots = frappe.get_all(
		"Server Snapshot",
		filters={
			"status": "Pending",
			"app_server_snapshot": ("is", "set"),
			"database_server_snapshot": ("is", "set"),
			"app_server_services_started": 1,
			"database_server_services_started": 1,
		},
		pluck="name",
	)

	for snapshot in pending_snapshots:
		with contextlib.suppress(Exception):
			current_status = frappe.db.get_value("Server Snapshot", snapshot, "status")
			if current_status == "Pending":
				# If the snapshot is still pending, update its status to Processing
				frappe.db.set_value("Server Snapshot", snapshot, "status", "Processing", update_modified=True)
				frappe.db.commit()


def expire_snapshots():
	records = frappe.get_all(
		"Server Snapshot",
		filters={
			"status": "Completed",
			"expire_at": ("<=", frappe.utils.now_datetime()),
			"locked": 0,
		},
		pluck="name",
		limit_page_length=50,
	)

	for record in records:
		try:
			snapshot = frappe.get_doc("Server Snapshot", record)
			snapshot.delete_snapshots()
			frappe.db.commit()
		except Exception:
			frappe.log_error("Server Snapshot Expire Error")
