# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.remote_file.remote_file import RemoteFile


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

	@frappe.whitelist()
	def download_binlog(self):
		frappe.enqueue_doc(
			"MariaDB Binlog",
			self.name,
			"_download_binlog",
			queue="default",
			timeout=300,
			now=True,
		)
		frappe.msgprint(
			"Binlog download started. You will be notified when the download is complete.",
		)

	def _download_binlog(self):
		if not self.uploaded:
			return
		remote_file: RemoteFile = frappe.get_doc("Remote File", self.remote_file)
		download_link = remote_file.get_download_link()
		if not download_link:
			return

		command = f"curl -sSL '{download_link}' | gunzip -c > /var/lib/mysql/{self.file_name}.bak"
		db = frappe.get_value(
			"Database Server", self.database_server, ("ip", "private_ip", "cluster"), as_dict=True
		)
		result = AnsibleAdHoc(sources=[db]).run(command, self.name, raw_params=True)[0]
		if not result.get("success"):
			pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
			comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
			self.add_comment(text=comment)
		else:
			self.add_comment(text=f"Binlog downloaded successfully to /var/lib/mysql/{self.file_name}.bak")


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
