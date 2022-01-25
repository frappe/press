# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
import json
from frappe.desk.doctype.tag.tag import add_tag


def execute():
	frappe.reload_doc("press", "doctype", "site_backup")
	bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")
	offsite_backups = [
		frappe.get_doc("Site Backup", x["name"])
		for x in frappe.get_all("Site Backup", {"offsite": 1})
	]

	for offsite_backup in offsite_backups:
		offsite_job_payload = json.loads(offsite_backup.offsite_backup or "{}")
		if offsite_job_payload:
			remote_database = offsite_job_payload.get(offsite_backup.get("database_file"))
			remote_public = offsite_job_payload.get(offsite_backup.get("public_file"))
			remote_private = offsite_job_payload.get(offsite_backup.get("private_file"))

			if remote_database:
				remote_file = frappe.get_doc(
					{
						"doctype": "Remote File",
						"file_name": offsite_backup.database_file,
						"file_path": remote_database,
						"file_size": offsite_backup.database_size,
						"file_type": "application/x-gzip",
						"bucket": bucket,
					}
				)
				remote_file.save()
				add_tag("Offsite Backup", remote_file.doctype, remote_file.name)
				offsite_backup.remote_database_file = remote_file.name

			if remote_public:
				remote_file = frappe.get_doc(
					{
						"doctype": "Remote File",
						"file_name": offsite_backup.public_file,
						"file_path": remote_public,
						"file_size": offsite_backup.public_size,
						"file_type": "application/x-tar",
						"bucket": bucket,
					}
				)
				remote_file.save()
				add_tag("Offsite Backup", remote_file.doctype, remote_file.name)
				offsite_backup.remote_public_file = remote_file.name

			if remote_private:
				remote_file = frappe.get_doc(
					{
						"doctype": "Remote File",
						"file_name": offsite_backup.private_file,
						"file_path": remote_private,
						"file_size": offsite_backup.private_size,
						"file_type": "application/x-tar",
						"bucket": bucket,
					}
				)
				remote_file.save()
				add_tag("Offsite Backup", remote_file.doctype, remote_file.name)
				offsite_backup.remote_private_file = remote_file.name

			offsite_backup.save()

	frappe.db.commit()
