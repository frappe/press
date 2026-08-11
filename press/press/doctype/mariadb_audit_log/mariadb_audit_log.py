# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document
from frappe.utils import add_days

from press.press.doctype.database_server.database_server import DatabaseServer
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


def to_mb(size_in_bytes: int) -> float:
	return round(size_in_bytes / (1024 * 1024), 2)


class MariaDBAuditLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		database_server: DF.Link
		end_time: DF.Datetime
		file_name: DF.Data
		remote_file: DF.Link | None
		size_mb: DF.Float
		start_time: DF.Datetime
		uncompressed_size_mb: DF.Float
	# end: auto-generated types

	def on_trash(self):
		self.delete_remote_file()

	def delete_remote_file(self):
		if not self.remote_file:
			return
		remote_file = self.remote_file
		# Cleared first so deleting the Remote File isn't blocked by this link
		self.db_set("remote_file", None)
		frappe.delete_doc("Remote File", remote_file)


def process_upload_audit_logs_to_s3_job_update(job: AgentJob):
	if job.status != "Success" or job.server_type != "Database Server" or not job.data:
		return

	offsite_files: dict = json.loads(job.data).get("offsite_files", {})
	if not offsite_files:
		return

	bucket = json.loads(job.request_data)["offsite"]["bucket"]
	for file_name, data in offsite_files.items():
		create_audit_log(job.server, bucket, file_name, data)


def create_audit_log(database_server: str, bucket: str, file_name: str, data: dict):
	if frappe.db.exists("MariaDB Audit Log", {"database_server": database_server, "file_name": file_name}):
		return

	remote_file = frappe.get_doc(
		{
			"doctype": "Remote File",
			"file_name": f"{file_name}.gz",
			"file_path": data["path"],
			"file_size": data["size"],
			"file_type": "application/x-gzip",
			"bucket": bucket,
		}
	).insert(ignore_permissions=True)
	add_tag("MariaDB Audit Log", remote_file.doctype, remote_file.name)

	frappe.get_doc(
		{
			"doctype": "MariaDB Audit Log",
			"database_server": database_server,
			"file_name": file_name,
			"start_time": data["start_timestamp"],
			"end_time": data["end_timestamp"],
			"size_mb": to_mb(data["size"]),
			"uncompressed_size_mb": to_mb(data["uncompressed_size"]),
			"remote_file": remote_file.name,
		}
	).insert(ignore_permissions=True)


def delete_expired_audit_logs():
	"""Drop audit logs past their server's retention window, and the S3 objects with them."""
	servers = frappe.get_all(
		"Database Server",
		filters={"audit_log_retention_days": (">", 0)},
		fields=["name", "audit_log_retention_days"],
	)
	for server in servers:
		if has_job_timeout_exceeded():
			return
		delete_expired_audit_logs_of_server(server.name, server.audit_log_retention_days)


def delete_expired_audit_logs_of_server(database_server: str, retention_days: int):
	expired = frappe.get_all(
		"MariaDB Audit Log",
		filters={
			"database_server": database_server,
			"end_time": ("<", add_days(None, -retention_days)),
		},
		pluck="name",
	)
	if not expired:
		return

	for name in expired:
		frappe.delete_doc("MariaDB Audit Log", name)
		# The S3 object goes with it, so a rollback would leave a row pointing at nothing
		frappe.db.commit()

	# Billing outlives disabling, so it ends here — once the last stored log is gone
	DatabaseServer("Database Server", database_server).sync_audit_log_subscription()
