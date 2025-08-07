# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site_backup.site_backup import get_backup_bucket

if TYPE_CHECKING:
	from press.press.doctype.server_snapshot.server_snapshot import ServerSnapshot
	from press.press.doctype.server_snapshot_site_recovery.server_snapshot_site_recovery import (
		ServerSnapshotSiteRecovery,
	)


class ServerSnapshotRecovery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app_server: DF.Link | None
		app_server_archived: DF.Check
		cluster: DF.Link
		database_server: DF.Link | None
		database_server_archived: DF.Check
		is_app_server_ready: DF.Check
		is_database_server_ready: DF.Check
		sites: DF.Table[ServerSnapshotSiteRecovery]
		snapshot: DF.Link
		status: DF.Literal[
			"Draft",
			"Creating Servers",
			"Gathering Site Data",
			"Warming Up",
			"Restoring",
			"Restored",
			"Failure",
		]
		team: DF.Link
		warm_up_end_time: DF.Datetime | None
	# end: auto-generated types

	dashboard_fields = (
		"status",
		"snapshot",
	)

	@property
	def server_agent(self) -> Agent:
		return frappe.get_doc("Server", self.app_server).agent

	def get_doc(self, doc):
		sites_data = []
		for s in self.sites:
			sites_data.append(
				{
					"site": s.site,
					"status": s.status,
					"database_backup_available": bool(s.database_remote_file),
					"public_files_backup_available": bool(s.public_remote_file),
					"private_files_backup_available": bool(s.private_remote_file),
					"encryption_key_available": bool(s.encryption_key),
				}
			)
		doc.sites_data = sites_data
		return doc

	def before_insert(self):
		self.validate_snapshot_status()
		self.fill_site_list()

	def after_insert(self):
		self.provision_servers()

	def validate_snapshot_status(self):
		snapshot: ServerSnapshot = frappe.get_doc(
			"Server Snapshot",
			self.snapshot,
		)
		if snapshot.status != "Completed":
			frappe.throw(f"Cannot recover from snapshot {snapshot.name} with status {snapshot.status}")

	def fill_site_list(self):
		sites_json = json.loads(
			frappe.get_value(
				"Server Snapshot",
				self.snapshot,
				"site_list",
			)
		)
		if not self.sites:
			self.sites = []

			for site in sites_json:
				self.append(
					"sites",
					{
						"site": site,
						"status": "Draft",
					},
				)
		else:
			for site in self.sites:
				if site.site not in sites_json:
					frappe.throw(f"Site {site.site} not available in snapshot {self.snapshot}")

		if len(self.sites) == 0:
			frappe.throw("Please choose at least one site to recover.")

	def on_update(self):
		if (
			self.status == "Creating Servers"
			and (
				self.has_value_changed("is_app_server_ready")
				or self.has_value_changed("is_database_server_ready")
			)
			and self.is_app_server_ready
			and self.is_database_server_ready
		):
			app_server_snaphot = frappe.get_value("Server Snapshot", self.snapshot, "app_server_snapshot")
			database_server_snaphot = frappe.get_value(
				"Server Snapshot", self.snapshot, "database_server_snapshot"
			)
			snapshot_warmup_minutes = int(
				(
					max(
						frappe.get_value("Virtual Disk Snapshot", app_server_snaphot, "size"),
						frappe.get_value("Virtual Disk Snapshot", database_server_snaphot, "size"),
					)
					* 1024
				)
				/ 300
				/ 60
			)  # Assuming 300 MB/s warmup speed
			self.warm_up_end_time = add_to_date(minutes=snapshot_warmup_minutes)
			self.status = "Warming Up"
			self.save()

		if self.has_value_changed("status") and self.status == "Restored":
			self.send_restoration_completion_email()
			self.archive_servers()

		if (
			(
				self.has_value_changed("app_server_archived")
				or self.has_value_changed("database_server_archived")
			)
			and self.app_server_archived
			and self.database_server_archived
			and self.status != "Restored"
		):
			self.status = "Failure"
			self.save()

	@frappe.whitelist()
	def provision_servers(self):
		self.validate_snapshot_status()
		self.status = "Creating Servers"
		snapshot: ServerSnapshot = frappe.get_doc(
			"Server Snapshot",
			self.snapshot,
		)

		self.database_server = snapshot.create_server(
			server_type="Database Server", temporary_server=True, is_for_recovery=True
		)
		self.app_server = snapshot.create_server(
			server_type="Server",
			temporary_server=True,
			database_server=self.database_server,
			is_for_recovery=True,
		)
		self.save()

	@frappe.whitelist()
	def archive_servers(self):
		if not self.app_server or not self.database_server:
			frappe.throw("Servers are not provisioned yet.")

		app_server_doc = frappe.get_doc("Server", self.app_server)
		if app_server_doc.status != "Archived":
			app_server_doc.archive()

		database_server_doc = frappe.get_doc("Database Server", self.database_server)
		if database_server_doc.status != "Archived":
			database_server_doc.archive()

	def send_restoration_completion_email(self):
		frappe.sendmail(
			subject="Snapshot Recovery Completed",
			recipients=[frappe.get_value("Team", self.team, "notify_email")],
			template="snapshot_recovery_completion",
			args={"snapshot": self.snapshot},
		)

	def mark_server_provisioning_as_failed(self):
		self.status = "Failure"
		self.save()

	def mark_process_as_failed(self):
		self.status = "Failure"
		for site in self.sites:
			site.status = "Failure"
		self.save()

	def fetch_sites_data(self):
		self.status = "Gathering Site Data"
		self.save()
		sites = [i.site for i in self.sites]
		self.server_agent.search_sites_in_snapshot(
			sites, reference_doctype=self.doctype, reference_name=self.name
		)

	def backup_sites(self):
		self.status = "Restoring"
		for site in self.sites:
			if site.status == "Pending":
				site.status = "Running"
				site.file_backup_job = self.server_agent.backup_site_files_from_snapshot(
					self.cluster,
					site.site,
					site.bench,
					reference_doctype=self.doctype,
					reference_name=self.name,
				)
				site.database_backup_job = self.server_agent.backup_site_database_from_snapshot(
					self.cluster,
					site.site,
					site.database_name,
					self.database_server,
					reference_doctype=self.doctype,
					reference_name=self.name,
				)

		self.save()

	def _check_site_recovery_status(self, save=False):
		pending_restoration = False
		for site in self.sites:
			if (
				site.status != "Failure"
				and site.public_remote_file
				and site.private_remote_file
				and site.database_remote_file
			):
				site.status = "Success"
			if site.status in ["Draft", "Pending", "Running"]:
				pending_restoration = True

		if not pending_restoration:
			self.status = "Restored"

		if save:
			self.save()

	def _process_backup_files_from_snapshot_job_callback(self, job: AgentJob):  # noqa: C901
		if job.status not in ["Success", "Failure"]:
			return
		site = json.loads(job.request_data or "{}").get("site")
		if not site:
			return

		site_record = None
		for s in self.sites:
			if s.site == site:
				site_record = s
				break

		if not site_record:
			frappe.throw(f"Site {site} not found in recovery sites.")

		if job.status == "Failure":
			site_record.status = "Failure"
		else:
			data = json.loads(job.data or "{}")
			if not data:
				site_record.status = "Failure"
				return
			for file, file_data in data.get("backup_files", {}).items():
				remote_file = self._create_remote_file(
					file_name=file_data.get("file"),
					file_path=data.get("offsite_files").get(file),
					file_size=file_data.get("size"),
				)
				if file.endswith("private_files.tar.gz"):
					site_record.private_remote_file = remote_file.name
				if file.endswith("public_files.tar.gz"):
					site_record.public_remote_file = remote_file.name

		self._check_site_recovery_status(save=True)

	def _process_backup_database_from_snapshot_job_callback(self, job: AgentJob):
		if job.status not in ["Success", "Failure"]:
			return
		site = json.loads(job.request_data or "{}").get("site")
		if not site:
			return

		site_record = None
		for s in self.sites:
			if s.site == site:
				site_record = s
				break
		if not site_record:
			frappe.throw(f"Site {site} not found in recovery sites.")

		if job.status == "Failure":
			site_record.status = "Failure"
		else:
			data = json.loads(job.data or "{}")
			if not data:
				site_record.status = "Failure"
				return
			remote_file = self._create_remote_file(
				file_name=data.get("backup_file"),
				file_path=data.get("offsite_files").get(data.get("backup_file")),
				file_size=data.get("backup_file_size"),
			)
			site_record.database_remote_file = remote_file.name

		self._check_site_recovery_status(save=True)

	def _create_remote_file(self, file_name: str, file_path: str, file_size: int):
		bucket = get_backup_bucket(self.cluster)
		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"file_name": file_name,
				"file_path": file_path,
				"file_size": file_size,
				"file_type": "application/x-gzip" if file_name.endswith(".gz") else "application/x-tar",
				"bucket": bucket,
			}
		)
		remote_file.save()
		return remote_file

	@dashboard_whitelist()
	def download_backup(self, site: str, file_type: str):  # noqa: C901
		"""
		Download the backup file for the given site and file type.
		"""
		if file_type not in ["public", "private", "database", "encryption_key"]:
			frappe.throw(
				f"Invalid file type: {file_type}. Must be one of 'public', 'private', 'database', or 'encryption_key'."
			)

		site_record: ServerSnapshotSiteRecovery = None
		for record in self.sites:
			if record.site == site:
				site_record = record
				break

		if not site_record:
			frappe.throw(f"Site {site} not found in recovery sites.")

		if (
			(file_type == "public" and not site_record.public_remote_file)
			or (file_type == "private" and not site_record.private_remote_file)
			or (file_type == "database" and not site_record.database_remote_file)
			or (file_type == "encryption_key" and not site_record.encryption_key)
		):
			frappe.throw(f"{file_type.capitalize()} backup not available for site {site}.")

		try:
			remote_file_name = ""
			if file_type == "public":
				remote_file_name = site_record.public_remote_file
			elif file_type == "private":
				remote_file_name = site_record.private_remote_file
			elif file_type == "database":
				remote_file_name = site_record.database_remote_file
			elif file_type == "encryption_key":
				return site_record.get_password("encryption_key")

			return frappe.get_doc("Remote File", remote_file_name).download_link
		except Exception:
			frappe.throw(f"Error downloading {file_type} backup for site {site}. Please try again later.")


def resume_warmed_up_restorations():
	records = frappe.get_all(
		"Server Snapshot Recovery",
		filters={
			"status": "Warming Up",
			"warm_up_end_time": ("<=", frappe.utils.now_datetime()),
		},
		fields=["name"],
	)

	for record in records:
		try:
			snapshot_recovery = frappe.get_doc("Server Snapshot Recovery", record.name)
			snapshot_recovery.fetch_sites_data()
			frappe.db.commit()
		except Exception:
			frappe.log_error("Server Snapshot Recovery Resume Error")


def process_search_sites_in_snapshot_job_callback(job: AgentJob):
	if job.status not in ["Success", "Failure"]:
		return

	if job.reference_doctype != "Server Snapshot Recovery" or not job.reference_name:
		return

	record: ServerSnapshotRecovery = frappe.get_doc("Server Snapshot Recovery", job.reference_name)

	if job.status == "Failure":
		record.mark_process_as_failed()
		return

	if job.status == "Success":
		data = json.loads(job.data or "{}")

		for site in record.sites:
			if site.site not in data:
				site.status = "Unavailable"
			else:
				site.status = "Pending"
				site.bench = data[site.site].get("bench", "")
				site.database_name = data[site.site].get("db_name", "")
				site.encryption_key = data[site.site].get("encryption_key", "")

		record.save()
		record.backup_sites()


def process_backup_files_from_snapshot_job_callback(job: AgentJob):
	if job.status not in ["Success", "Failure"]:
		return

	if job.reference_doctype != "Server Snapshot Recovery" or not job.reference_name:
		return

	record: ServerSnapshotRecovery = frappe.get_doc(
		"Server Snapshot Recovery", job.reference_name, for_update=True
	)
	record._process_backup_files_from_snapshot_job_callback(job)


def process_backup_database_from_snapshot_job_callback(job: AgentJob):
	if job.status not in ["Success", "Failure"]:
		return

	if job.reference_doctype != "Server Snapshot Recovery" or not job.reference_name:
		return

	record: ServerSnapshotRecovery = frappe.get_doc(
		"Server Snapshot Recovery", job.reference_name, for_update=True
	)
	record._process_backup_database_from_snapshot_job_callback(job)
