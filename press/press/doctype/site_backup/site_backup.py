# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import json
from datetime import datetime
from typing import Dict

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document
from press.agent import Agent


class SiteBackup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		config_file: DF.Data | None
		config_file_size: DF.Data | None
		config_file_url: DF.Text | None
		database: DF.Data | None
		database_file: DF.Data | None
		database_size: DF.Data | None
		database_url: DF.Text | None
		files_availability: DF.Literal["", "Available", "Unavailable"]
		job: DF.Link | None
		offsite: DF.Check
		offsite_backup: DF.Code | None
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
		size: DF.Data | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		url: DF.Data | None
		with_files: DF.Check
	# end: auto-generated types

	dashboard_fields = [
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
	]

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

	def after_insert(self):
		site = frappe.get_doc("Site", self.site)
		agent = Agent(site.server)
		job = agent.backup_site(site, self.with_files, self.offsite)
		frappe.db.set_value("Site Backup", self.name, "job", job.name)

	def after_delete(self):
		if self.job:
			frappe.delete_doc_if_exists("Agent Job", self.job)

	@classmethod
	def offsite_backup_exists(cls, site: str, day: datetime.date) -> bool:
		return cls.backup_exists(site, day, {"offsite": True})

	@classmethod
	def backup_exists(cls, site: str, day: datetime.date, filters: Dict):
		base_filters = {
			"creation": ("between", [day, day]),
			"site": site,
			"status": "Success",
		}
		return frappe.get_all("Site Backup", {**base_filters, **filters})

	@classmethod
	def file_backup_exists(cls, site: str, day: datetime.date) -> bool:
		return cls.backup_exists(site, day, {"with_files": True})


def track_offsite_backups(
	site: str, backup_data: dict, offsite_backup_data: dict
) -> tuple:
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


def process_backup_site_job_update(job):
	backups = frappe.get_all(
		"Site Backup", fields=["name", "status"], filters={"job": job.name}, limit=1
	)
	if not backups:
		return
	backup = backups[0]
	if job.status != backup.status:
		frappe.db.set_value("Site Backup", backup.name, "status", job.status)
		if job.status == "Success":
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
	bucket_for_cluster = frappe.get_all(
		"Backup Bucket", {"cluster": cluster}, ["name", "region"], limit=1
	)
	default_bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")

	if region:
		return bucket_for_cluster[0] if bucket_for_cluster else default_bucket
	else:
		return bucket_for_cluster[0]["name"] if bucket_for_cluster else default_bucket


def on_doctype_update():
	frappe.db.add_index("Site Backup", ["files_availability", "job"])
