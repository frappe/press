# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import time

import frappe
from frappe.exceptions import DoesNotExistError
from frappe.model.document import Document

from press.agent import Agent


class PhysicalBackupGroupSite(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		backup: DF.Link | None
		backup_available: DF.Check
		db_size: DF.Int
		duration_seconds: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		site: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	def set_db_size(self):
		if self.db_size:
			return
		doc = frappe.get_doc("Site", self.site)
		self.db_size = doc.current_usage["database"]
		self.save()

	def sync(self):
		if not self.backup:
			return
		try:
			backup = frappe.get_doc("Site Backup", self.backup)
			if backup.database_snapshot:
				# sync status of snapshot
				frappe.get_doc("Virtual Disk Snapshot", backup.database_snapshot).sync()
				backup.reload()
			if backup.status == "Pending":
				self.status = "Running"
			else:
				self.status = backup.status
			self.backup_available = backup.files_availability == "Available"
		except DoesNotExistError:
			self.backup = None
			self.backup_available = False
		self.save()

	def physical_backup(self):
		start_time = time.time()
		site = frappe.get_doc("Site", self.site)
		agent = Agent(site.server)
		try:
			deactivate_job = agent.deactivate_site(site)
			deactivate_job_status = deactivate_job.status
			while True:
				deactivate_job_status = frappe.get_value("Agent Job", deactivate_job.name, "status")
				frappe.db.commit()
				if deactivate_job_status in ("Success", "Failure", "Delivery Failure"):
					break
				time.sleep(1)

			if deactivate_job_status != "Success":
				self.status = "Failure"
				self.save()
				return

			# backup site
			backup = site.physical_backup()
			self.backup = backup.name
			self.save()

			backup_status = backup.status
			while True:
				backup_status = frappe.get_value("Site Backup", self.backup, "status")
				frappe.db.commit()
				if backup_status in ("Success", "Failure"):
					break
				time.sleep(5)

			if backup_status == "Success":
				self.status = "Success"
			else:
				self.status = "Failure"
			duration = time.time() - start_time
			self.duration_seconds = int(duration)
			self.save()
		except Exception:
			frappe.log_error(title="Error while bulk physical backup")
		finally:
			agent.activate_site(site)

	def delete_backup(self):
		if not self.backup:
			return
		database_snapshot = frappe.get_value("Site Backup", self.backup, "database_snapshot")
		if database_snapshot:
			frappe.get_doc("Virtual Disk Snapshot", database_snapshot).delete_snapshot()

	# def on_update(self):
	# 	if self.has_value_changed("status") and self.status in ("Success", "Failure"):
	# 		# trigger next backup
	# 		frappe.enqueue_doc("Physical Backup Group", self.parent, "_trigger_next_backup", queue="default")
