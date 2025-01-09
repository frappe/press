# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document

from press.agent import Agent

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
		myisam_tables: DF.Code | None
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

	def validate(self):
		if self.physical and self.with_files:
			frappe.throw("Physical backups cannot be taken with files")
		if self.physical and self.offsite:
			frappe.throw("Physical and offsite logical backups cannot be taken together")

	def before_insert(self):
		if getattr(self, "force", False):
			return
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
			site = frappe.get_doc("Site", self.site)
			if not site.database_name:
				site.sync_info()
				site.reload()
			if not site.database_name:
				frappe.throw("Database name is missing in the site")
			self.database_name = site.database_name

	def after_insert(self):
		site = frappe.get_doc("Site", self.site)
		agent = Agent(site.server)
		if self.physical:
			job = agent.physical_backup_database(site, self)
		else:
			job = agent.backup_site(site, self)
		frappe.db.set_value("Site Backup", self.name, "job", job.name)

	def after_delete(self):
		if self.job:
			frappe.delete_doc_if_exists("Agent Job", self.job)

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

		frappe.db.set_value("Site Backup", backup.name, "status", status)
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
