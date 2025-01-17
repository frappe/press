# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from datetime import datetime


class SiteBackup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		config_file: DF.Data | None
		config_file_size: DF.Data | None
		config_file_url: DF.Text | None
		database_file: DF.Data | None
		database_name: DF.Data | None
		database_size: DF.Data | None
		database_snapshot: DF.Link | None
		database_url: DF.Text | None
		files_availability: DF.Literal["", "Available", "Unavailable"]
		innodb_tables: DF.JSON | None
		job: DF.Link | None
		myisam_tables: DF.JSON | None
		offsite: DF.Check
		offsite_backup: DF.Code | None
		physical: DF.Check
		private_file: DF.Data | None
		private_size: DF.Data | None
		private_url: DF.Text | None
		public_file: DF.Data | None
		public_size: DF.Data | None
		public_url: DF.Text | None
		remote_config_file: DF.Link | None
		remote_database_file: DF.Link | None
		remote_private_file: DF.Link | None
		remote_public_file: DF.Link | None
		site: DF.Link
		snapshot_request_key: DF.Data | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		table_schema: DF.Code | None
		team: DF.Link | None
		with_files: DF.Check
	# end: auto-generated types

	dashboard_fields = (
		"job",
		"status",
		"database_url",
		"public_url",
		"private_url",
		"config_file_url",
		"site",
		"database_size",
		"public_size",
		"private_size",
		"with_files",
		"offsite",
		"files_availability",
		"remote_database_file",
		"remote_public_file",
		"remote_private_file",
		"remote_config_file",
	)

	@property
	def database_server(self):
		server = frappe.get_value("Site", self.site, "server")
		return frappe.get_value("Server", server, "database_server")

	def validate(self):
		if self.physical and self.with_files:
			frappe.throw("Physical backups cannot be taken with files")
		if self.physical and self.offsite:
			frappe.throw("Physical and offsite logical backups cannot be taken together")

	def before_insert(self):
		if getattr(self, "force", False):
			if self.physical:
				frappe.throw("Physical backups cannot be forcefully triggered")
			return
		# For backups, check if there are too many pending backups
		two_hours_ago = frappe.utils.add_to_date(None, hours=-2)
		if frappe.db.count(
			"Site Backup",
			{
				"site": self.site,
				"status": ("in", ["Running", "Pending"]),
				"creation": (">", two_hours_ago),
			},
		):
			frappe.throw("Too many pending backups")

		if self.physical:
			# Set some default values
			site = frappe.get_doc("Site", self.site)
			if not site.database_name:
				site.sync_info()
				site.reload()
			if not site.database_name:
				frappe.throw("Database name is missing in the site")
			self.database_name = site.database_name
			self.snapshot_request_key = frappe.generate_hash(length=32)

	def after_insert(self):
		if self.physical:
			frappe.enqueue_doc(
				doctype=self.doctype,
				name=self.name,
				method="_create_physical_backup",
				enqueue_after_commit=True,
			)
		else:
			site = frappe.get_doc("Site", self.site)
			agent = Agent(self.database_server, "Database Server")
			job = agent.backup_site(site, self)
			frappe.db.set_value("Site Backup", self.name, "job", job.name)

	def after_delete(self):
		if self.job:
			frappe.delete_doc_if_exists("Agent Job", self.job)

	def on_update(self):
		print("on_update")
		print(self.has_value_changed("status"))
		print(self.status)
		print(self.physical)
		if self.physical and self.has_value_changed("status") and self.status in ["Success", "Failure"]:
			"""
			Rollback the permission changes made to the database directory
			Change it back to 770 from 700

			Check `_create_physical_backup` method for more information
			"""
			success = self.run_ansible_command_in_database_server(
				f"chmod 700 /var/lib/mysql/{self.database_name}"
			)
			print(success)
			if not success:
				"""
				Don't throw an error here, Because the backup is already created
				And keeping the permission as 770 will not cause issue in database operations
				"""
				frappe.log_error(
					"Failed to rollback the permission changes of the database directory",
					reference_doctype=self.doctype,
					reference_name=self.name,
				)

	def _create_physical_backup(self):
		site = frappe.get_doc("Site", self.site)
		"""
		Change the /var/lib/mysql/<database_name> directory's permission to 770 from 770
		The files inside that directory will have 660 permission, So no need to change the permission of the files

		`frappe` user on server is already part of `mysql` group.
		So `frappe` user can read-write the files inside that directory
		"""
		success = self.run_ansible_command_in_database_server(
			f"chmod 770 /var/lib/mysql/{self.database_name}"
		)
		if not success:
			frappe.db.set_value("Site Backup", self.name, "status", "Failure")
			return
		agent = Agent(self.database_server, "Database Server")
		job = agent.physical_backup_database(site, self)
		frappe.db.set_value("Site Backup", self.name, "job", job.name)

	def run_ansible_command_in_database_server(self, command: str) -> bool:
		virtual_machine_ip = frappe.db.get_value(
			"Virtual Machine",
			frappe.get_value("Database Server", self.database_server, "virtual_machine"),
			"public_ip_address",
		)
		result = AnsibleAdHoc(sources=f"{virtual_machine_ip},").run(command, self.name)[0]
		success = result.get("status") == "Success"
		if not success:
			pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
			frappe.log_error(
				"During physical backup creation, failed to execute command in database server",
				message=pretty_result,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)
			comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
			self.add_comment(text=comment)
		return success

	def create_database_snapshot(self):
		if self.database_snapshot:
			# Snapshot already exists, So no need to create a new one
			return
		server = frappe.get_value("Site", self.site, "server")
		database_server = frappe.get_value("Server", server, "database_server")
		virtual_machine = frappe.get_doc(
			"Virtual Machine", frappe.get_value("Database Server", database_server, "virtual_machine")
		)
		virtual_machine.create_snapshots(exclude_boot_volume=True)
		if len(virtual_machine.flags.created_snapshots) == 0:
			frappe.throw("Failed to create a snapshot for the database server")
		frappe.db.set_value(
			"Site Backup", self.name, "database_snapshot", virtual_machine.flags.created_snapshots[0]
		)

	@classmethod
	def offsite_backup_exists(cls, site: str, day: datetime.date) -> bool:
		return cls.backup_exists(site, day, {"offsite": True})

	@classmethod
	def backup_exists(cls, site: str, day: datetime.date, filters: dict):
		base_filters = {
			"creation": ("between", [day, day]),
			"site": site,
			"status": "Success",
		}
		return frappe.get_all("Site Backup", {**base_filters, **filters})

	@classmethod
	def file_backup_exists(cls, site: str, day: datetime.date) -> bool:
		return cls.backup_exists(site, day, {"with_files": True})


def track_offsite_backups(site: str, backup_data: dict, offsite_backup_data: dict) -> tuple:
	remote_files = {"database": None, "site_config": None, "public": None, "private": None}

	if offsite_backup_data:
		bucket = get_backup_bucket(frappe.db.get_value("Site", site, "cluster"))
		for type, backup in backup_data.items():
			file_name, file_size = backup["file"], backup["size"]
			file_path = offsite_backup_data.get(file_name)

			file_types = {
				"database": "application/x-gzip",
				"site_config": "application/json",
			}
			if file_path:
				remote_file = frappe.get_doc(
					{
						"doctype": "Remote File",
						"site": site,
						"file_name": file_name,
						"file_path": file_path,
						"file_size": file_size,
						"file_type": file_types.get(type, "application/x-tar"),
						"bucket": bucket,
					}
				)
				remote_file.save()
				add_tag("Offsite Backup", remote_file.doctype, remote_file.name)
				remote_files[type] = remote_file.name

	return (
		remote_files["database"],
		remote_files["site_config"],
		remote_files["public"],
		remote_files["private"],
	)


def process_backup_site_job_update(job):  # noqa: C901
	backups = frappe.get_all("Site Backup", fields=["name", "status"], filters={"job": job.name}, limit=1)
	if not backups:
		return
	backup = backups[0]
	if job.status != backup.status:
		status = job.status
		if job.status == "Delivery Failure":
			status = "Failure"

		if job.status == "Success":
			if frappe.get_value("Site Backup", backup.name, "physical"):
				site_backup: SiteBackup = frappe.get_doc("Site Backup", backup.name)
				data = json.loads(job.data)
				if site_backup.database_name not in data:
					frappe.log_error("[Failure] Database name not found in the backup data", data=job.data)
					site_backup.status = "Failure"
				else:
					site_backup.innodb_tables = json.dumps(data[site_backup.database_name]["innodb_tables"])
					site_backup.myisam_tables = json.dumps(data[site_backup.database_name]["myisam_tables"])
					site_backup.table_schema = data[site_backup.database_name]["table_schema"]
					site_backup.status = "Success"
				site_backup.save()
			else:
				frappe.db.set_value("Site Backup", backup.name, "status", status)
				job_data = json.loads(job.data)
				backup_data, offsite_backup_data = job_data["backups"], job_data["offsite"]
				(
					remote_database,
					remote_config_file,
					remote_public,
					remote_private,
				) = track_offsite_backups(job.site, backup_data, offsite_backup_data)

				site_backup_dict = {
					"files_availability": "Available",
					"database_size": backup_data["database"]["size"],
					"database_url": backup_data["database"]["url"],
					"database_file": backup_data["database"]["file"],
					"remote_database_file": remote_database,
				}

				if "site_config" in backup_data:
					site_backup_dict.update(
						{
							"config_file_size": backup_data["site_config"]["size"],
							"config_file_url": backup_data["site_config"]["url"],
							"config_file": backup_data["site_config"]["file"],
							"remote_config_file": remote_config_file,
						}
					)

				if "private" in backup_data and "public" in backup_data:
					site_backup_dict.update(
						{
							"private_size": backup_data["private"]["size"],
							"private_url": backup_data["private"]["url"],
							"private_file": backup_data["private"]["file"],
							"remote_public_file": remote_public,
							"public_size": backup_data["public"]["size"],
							"public_url": backup_data["public"]["url"],
							"public_file": backup_data["public"]["file"],
							"remote_private_file": remote_private,
						}
					)

				frappe.db.set_value("Site Backup", backup.name, site_backup_dict)


def get_backup_bucket(cluster, region=False):
	bucket_for_cluster = frappe.get_all("Backup Bucket", {"cluster": cluster}, ["name", "region"], limit=1)
	default_bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")

	if region:
		return bucket_for_cluster[0] if bucket_for_cluster else default_bucket
	return bucket_for_cluster[0]["name"] if bucket_for_cluster else default_bucket


def on_doctype_update():
	frappe.db.add_index("Site Backup", ["files_availability", "job"])
