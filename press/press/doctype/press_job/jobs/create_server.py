import contextlib
from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server_snapshot_recovery.server_snapshot_recovery import ServerSnapshotRecovery
	from press.press.doctype.virtual_machine_image.virtual_machine_image import VirtualMachineImage


class CreateServerJob(PressJob):
	@flow
	def execute(self):
		self.provision_server()
		self.wait_for_server_to_start()
		self.wait_for_server_to_be_accessible()
		self.sync_default_volumes()

		if self.virtual_machine_doc.data_disk_snapshot:
			self.create_volume_from_snapshot()
			self.attach_snapshotted_volume()
			self.sync_attached_volumes()
			self.mount_snapshotted_volume()

		self.check_cloud_init_status()

		if self.server_doc.provider == "Hetzner" and self.virtual_machine:
			self.create_and_mount_volumes_hetzner()
			self.configure_apps_for_mounts_hetzner()

		self.update_tls_certificate()
		self.update_agent()

		if self.server_type == "Database Server" or (
			self.server_type == "Server" and self.server_doc.is_unified_server
		):
			self.upgrade_mariadb()

		if self.is_setup_db_replication:
			self.prepare_mariadb_replica()
			self.configure_mariadb_replica()
			self.start_mariadb_replica()

		self.set_additional_config()

		if self.is_fs_server:
			self.share_benches_over_nfs()

	@property
	def is_setup_db_replication(self):
		return self.server_type == "Database Server" and self.arguments_dict.get(
			"setup_db_replication", False
		)

	@property
	def is_fs_server(self):
		return self.server.startswith("fs") and self.server_type == "Server"

	@task
	def provision_server(self):
		machine = self.virtual_machine_doc
		if machine.status != "Draft":
			return
		machine.provision()

	@task
	def wait_for_server_to_start(self):
		retry_later = True
		try:
			self.virtual_machine_doc.sync()
		except (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError):
			retry_later = True
		except Exception as e:
			if "rate_limit_exceeded" in str(e):
				retry_later = True
			else:
				raise e

		if self.virtual_machine_doc.status == "Running":
			retry_later = False

		if retry_later:
			self.defer_current_task()

	@task
	def wait_for_server_to_be_accessible(self):
		server = self.server_doc
		play = server.ping_ansible()
		if not play or play.status != "Success":
			self.defer_current_task()

		self.virtual_machine_doc.reload()
		if not self.virtual_machine_doc.private_ip_address:
			raise Exception("Virtual machine does not have a private IP address yet")

	@task
	def sync_default_volumes(self):
		try:
			self.virtual_machine_doc.sync()
			if len(self.virtual_machine_doc.volumes) > 0:
				return
		except (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError):
			pass

		self.defer_current_task()

	@task
	def create_volume_from_snapshot(self):
		if not self.virtual_machine_doc.data_disk_snapshot:
			return

		if self.virtual_machine_doc.data_disk_snapshot_volume_id:
			# Volume has already been created from the snapshot, proceed to attach it
			return

		max_retries = self.arguments_dict.get("max_volume_creation_retries", 6)
		if self.kv.get("volume_creation_attempts", 0) >= max_retries:
			raise Exception(f"Failed to create volume from snapshot after {max_retries} retries")

		is_created = self.virtual_machine_doc.create_data_disk_volume_from_snapshot()
		if is_created:
			return

		self.kv.set("volume_creation_attempts", self.kv.get("volume_creation_attempts", 0) + 1)
		self.defer_current_task()

	@task
	def attach_snapshotted_volume(self):
		if not self.virtual_machine_doc.data_disk_snapshot:
			return

		if self.virtual_machine_doc.data_disk_snapshot_attached:
			# Volume has already been attached, proceed to sync it
			return

		try:
			self.virtual_machine_doc.check_and_attach_data_disk_snapshot_volume()
		except (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError):
			self.defer_current_task()

	@task
	def sync_attached_volumes(self):
		if not self.virtual_machine_doc.data_disk_snapshot:
			return

		with contextlib.suppress(
			frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError
		):
			self.virtual_machine_doc.sync()
			if (
				self.virtual_machine_doc.data_disk_snapshot_attached
				and len(self.virtual_machine_doc.volumes) == 1
			) or (
				not self.virtual_machine_doc.data_disk_snapshot_attached
				and len(self.virtual_machine_doc.volumes) == 0
			):
				self.defer_current_task()
				return

			server = self.server_doc
			server.reload()
			server.validate_mounts()
			server.save()

	@task(queue="long", timeout=7200)
	def mount_snapshotted_volume(self):
		if self.server_doc.provider != "AWS EC2" or not self.virtual_machine_doc.data_disk_snapshot:
			return

		cleanup_db_replication_files = False
		if self.server_type == "Database Server" and (
			self.server_doc.is_for_recovery or self.is_setup_db_replication
		):
			cleanup_db_replication_files = True

		self.server_doc.mount_volumes(
			now=True,
			stop_docker_before_mount=self.server_type == "Server",
			stop_mariadb_before_mount=self.server_type == "Database Server",
			start_docker_after_mount=self.server_type == "Server" and not self.server_doc.is_for_recovery,
			start_mariadb_after_mount=not self.is_setup_db_replication,
			cleanup_db_replication_files=cleanup_db_replication_files,
			rotate_additional_volume_metadata=True,
		)

	@task(queue="short")
	def check_cloud_init_status(self):
		self.server_doc._wait_for_cloud_init()

	@task(queue="long", timeout=1200)
	def create_and_mount_volumes_hetzner(self):
		if self.server_doc.provider != "Hetzner" or not self.virtual_machine:
			return

		if not self.virtual_machine_doc.virtual_machine_image:
			return

		vmi: VirtualMachineImage = frappe.get_doc(
			"Virtual Machine Image", self.virtual_machine_doc.virtual_machine_image
		)
		if not vmi.has_data_volume:
			return

		server = self.server_doc
		if server.plan:
			data_disk_size = int(frappe.db.get_value("Server Plan", server.plan, "disk"))
		else:
			data_disk_size = 25

		self.virtual_machine_doc.attach_new_volume(data_disk_size)

		max_sync_tries = 100
		while max_sync_tries:
			try:
				self.virtual_machine_doc.sync()
				break
			except Exception as e:
				max_sync_tries -= 1
				if max_sync_tries <= 0:
					raise e

		server.validate_mounts()
		server.save(ignore_version=True)
		server.mount_volumes(now=True)

	@task(queue="long", timeout=1200)
	def configure_apps_for_mounts_hetzner(self):
		server = self.server_doc
		if server.provider != "Hetzner" or not getattr(server, "has_data_volume", False):
			return

		if server.doctype == "Server":
			server.setup_docker(now=True)
		elif server.doctype == "Database Server":
			server.set_mariadb_mount_dependency(now=True)

	@task
	def update_tls_certificate(self):
		self.server_doc.update_tls_certificate(throw_on_failure=True)

	@task
	def update_agent(self):
		self.server_doc._update_agent_ansible(throw_on_failure=True)

	@task(queue="long", timeout=1800)
	def upgrade_mariadb(self):
		if self.server_type == "Database Server":
			play = self.server_doc._upgrade_mariadb()
			if play.status != "Success":
				raise Exception("Failed to upgrade MariaDB")

		if self.server_type == "Server" and self.server_doc.is_unified_server:
			database_server: DatabaseServer = frappe.get_doc(
				"Database Server", self.server_doc.database_server
			)
			database_server._upgrade_mariadb()

	@task(queue="long", timeout=1200)
	def prepare_mariadb_replica(self):
		if not self.is_setup_db_replication:
			return

		self.server_doc._prepare_mariadb_replica(throw_on_failure=True)

	@task
	def configure_mariadb_replica(self):
		if not self.is_setup_db_replication:
			return

		self.server_doc.configure_replication()

	@task
	def start_mariadb_replica(self):
		if not self.is_setup_db_replication:
			return

		self.server_doc.start_replication()

	@task
	def set_additional_config(self):
		self.server_doc.set_additional_config()

	@task
	def share_benches_over_nfs(self):
		if self.server.startswith("fs") and self.server_type == "Server":
			primary_server = frappe.db.get_value("Server", self.server, "primary")
			nfs_volume_attachment = frappe.get_doc(
				{"doctype": "NFS Volume Attachment", "primary_server": primary_server}
			)
			nfs_volume_attachment.insert(ignore_permissions=True)

	# Callbacks
	def on_press_job_success(self, _):
		args = self.arguments_dict

		# Mark provisioning flag of the server
		if self.server_type in ["Server", "Database Server"]:
			self.server_doc.is_provisioning_press_job_completed = 1
			self.server_doc.save(ignore_permissions=True)

		# In case of unified server, also mark linked database server as provisioned
		if self.server_type == "Server" and self.server_doc.is_unified_server:
			frappe.db.set_value(
				"Database Server",
				self.server_doc.database_server,
				"is_provisioning_press_job_completed",
				1,
				update_modified=False,
			)

		# Update "Server Snapshot Recovery" record if this server is being provisioned for recovery
		if self.server_type in ["Server", "Database Server"] and self.server_doc.is_for_recovery:
			recovery_record_name = frappe.db.get_value(
				"Server Snapshot Recovery",
				{
					"app_server" if self.server_type == "Server" else "database_server": self.server,
				},
				"name",
			)
			if recovery_record_name:
				recovery_record = frappe.get_doc(
					"Server Snapshot Recovery", recovery_record_name, for_update=True
				)
				if self.server_type == "Server":
					recovery_record.is_app_server_ready = True
				else:
					recovery_record.is_database_server_ready = True
				recovery_record.save()

		# Resume logical replication backup if it was setup as part of server provisioning
		if self.server_type in ["Server", "Database Server"] and "logical_replication_backup" in args:
			frappe.get_doc("Logical Replication Backup", args.get("logical_replication_backup")).next()

	def on_press_job_failure(self, _):
		if self.server_type not in ["Server", "Database Server"]:
			return

		# Mark Server Snapshot Recovery as failed if the server provisioning was for recovery
		if self.server_doc.is_for_recovery:
			recovery_record_name = frappe.db.get_value(
				"Server Snapshot Recovery",
				{"app_server" if self.server_type == "Server" else "database_server": self.server},
				"name",
			)
			if recovery_record_name:
				recovery_record: ServerSnapshotRecovery = frappe.get_doc(
					"Server Snapshot Recovery", recovery_record_name, for_update=True
				)
				recovery_record.mark_server_provisioning_as_failed()

		# Mark logical replication backup as failed if it was setup as part of server provisioning
		if "logical_replication_backup" in self.arguments_dict:
			frappe.get_doc(
				"Logical Replication Backup", self.arguments_dict.get("logical_replication_backup")
			).fail()
