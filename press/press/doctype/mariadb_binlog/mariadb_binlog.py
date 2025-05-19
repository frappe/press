# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document

if TYPE_CHECKING:
	from apps.press.press.press.doctype.agent_job.agent_job import AgentJob


class MariaDBBinlog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		current: DF.Check
		database_server: DF.Link
		file_modification_time: DF.Datetime
		file_name: DF.Data
		indexed: DF.Check
		purged_from_disk: DF.Check
		remote_file: DF.Link | None
		size_mb: DF.Float
		uploaded: DF.Check
	# end: auto-generated types

	def on_trash(self):
		self.delete_remote_file()

	def delete_remote_file(self):
		if self.remote_file:
			remote_file = self.remote_file
			self.uploaded = 0
			self.remote_file = None
			self.save()
			frappe.delete_doc("Remote File", remote_file)


def process_upload_binlogs_to_s3_job_update(job: AgentJob):
	if job.status != "Success" or job.server_type != "Database Server" or not job.data:
		return

	data: dict = json.loads(job.data)
	offsite_files: dict = data.get("offsite_files", {})
	if not offsite_files:
		return

	bucket = json.loads(job.request_data)["offsite"]["bucket"]

	binlog_file_remote_files = {}
	# Create remote file records for each file
	for binlog_file_name, data in offsite_files.items():
		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"file_name": f"{binlog_file_name}.gz",
				"file_path": data["path"],
				"file_size": data["size"],
				"file_type": "application/x-gzip",
				"bucket": bucket,
			}
		)
		remote_file.save()
		add_tag("MariaDB Binlog", remote_file.doctype, remote_file.name)
		binlog_file_remote_files[binlog_file_name] = remote_file.name

	# Update the remote_file field in the binlog files
	for binlog_file_name, remote_file_name in binlog_file_remote_files.items():
		frappe.db.set_value(
			"MariaDB Binlog",
			{"file_name": binlog_file_name, "database_server": job.server, "current": 0},
			{
				"uploaded": 1,
				"remote_file": remote_file_name,
			},
		)


def cleanup_old_records():
	"""
	Cleanup junk records
	"""
	frappe.db.delete(
		"MariaDB Binlog",
		{
			"purged_from_disk": 1,
			"uploaded": 0,
			"indexed": 0,
		},
	)
