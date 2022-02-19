# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import json
from datetime import datetime, timedelta
from typing import Dict

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document
from press.agent import Agent
from press.press.doctype.site_activity.site_activity import log_site_activity


class SiteBackup(Document):
	def before_insert(self):
		last_two_hours = datetime.now() - timedelta(hours=2)
		if frappe.db.count(
			"Site Backup",
			{
				"site": self.site,
				"status": ("in", ["Running", "Pending"]),
				"creation": (">", last_two_hours),
			},
		):
			raise Exception("Too many pending backups")

	def after_insert(self):
		log_site_activity(self.site, "Backup")
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
	remote_files = {"database": None, "public": None, "private": None}

	if offsite_backup_data:
		bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")
		for type, backup in backup_data.items():
			file_name, file_size = backup["file"], backup["size"]
			file_path = offsite_backup_data.get(file_name)

			if file_path:
				remote_file = frappe.get_doc(
					{
						"doctype": "Remote File",
						"site": site,
						"file_name": file_name,
						"file_path": file_path,
						"file_size": file_size,
						"file_type": "application/x-gzip" if type == "database" else "application/x-tar",
						"bucket": bucket,
					}
				)
				remote_file.save()
				add_tag("Offsite Backup", remote_file.doctype, remote_file.name)
				remote_files[type] = remote_file.name

	return remote_files["database"], remote_files["public"], remote_files["private"]


def process_backup_site_job_update(job):
	backup = frappe.get_all(
		"Site Backup", fields=["name", "status"], filters={"job": job.name}
	)[0]
	if job.status != backup.status:
		frappe.db.set_value(
			"Site Backup", backup.name, "status", job.status, for_update=False
		)
		if job.status == "Success":
			job_data = json.loads(job.data)
			backup_data, offsite_backup_data = job_data["backups"], job_data["offsite"]
			remote_database, remote_public, remote_private = track_offsite_backups(
				job.site, backup_data, offsite_backup_data
			)

			frappe.db.set_value(
				"Site Backup",
				backup.name,
				{
					"files_availability": "Available",
					"database_size": backup_data["database"]["size"],
					"database_url": backup_data["database"]["url"],
					"database_file": backup_data["database"]["file"],
					"remote_database_file": remote_database,
				},
				for_update=False,
			)
			if "private" in backup_data and "public" in backup_data:
				frappe.db.set_value(
					"Site Backup",
					backup.name,
					{
						"private_size": backup_data["private"]["size"],
						"private_url": backup_data["private"]["url"],
						"private_file": backup_data["private"]["file"],
						"remote_public_file": remote_public,
						"public_size": backup_data["public"]["size"],
						"public_url": backup_data["public"]["url"],
						"public_file": backup_data["public"]["file"],
						"remote_private_file": remote_private,
					},
					for_update=False,
				)
