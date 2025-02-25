# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.physical_backup_group.physical_backup_group import PhysicalBackupGroup
	from press.press.doctype.site_update.site_update import PhysicalBackupRestoration


class PhysicalRestorationTest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.physical_restoration_test_result.physical_restoration_test_result import (
			PhysicalRestorationTestResult,
		)

		backup_group: DF.Link
		completed: DF.Check
		destination_database: DF.Data | None
		destination_server: DF.Link | None
		max_restorations: DF.Int
		results: DF.Table[PhysicalRestorationTestResult]
		test_site: DF.Link
	# end: auto-generated types

	def validate(self):
		if not self.destination_server:
			self.destination_server = frappe.get_value(
				"Server", frappe.get_value("Site", self.test_site, "server"), "database_server"
			)
		if self.is_new():
			pass

	def after_insert(self):
		backup_group: PhysicalBackupGroup = frappe.get_doc("Physical Backup Group", self.backup_group)
		# set max restorations
		if not self.max_restorations or self.max_restorations > len(backup_group.site_backups):
			self.max_restorations = len(backup_group.site_backups)

		# populate results table
		records = backup_group.site_backups[: self.max_restorations]
		for record in records:
			self.append(
				"results",
				{
					"site": record.site,
					"db_size_mb": record.db_size,
					"restore_record": self._create_restoration_record(record.backup).name,
					"status": "Pending",
				},
			)

		self.save()

	def _create_restoration_record(self, site_backup: str) -> PhysicalBackupRestoration:
		return frappe.get_doc(
			{
				"doctype": "Physical Backup Restoration",
				"site": self.test_site,
				"status": "Pending",
				"site_backup": site_backup,
				"source_database": frappe.db.get_value("Site Backup", site_backup, "database_name"),
				"destination_database": self.destination_database,
				"destination_server": self.destination_server,
				"restore_specific_tables": False,
				"tables_to_restore": "[]",
				"physical_restoration_test": self.name,
			}
		).insert(ignore_permissions=True)

	@frappe.whitelist()
	def start(self):
		self.sync()
		record = None
		# check if there is any running restoration
		for result in self.results:
			if result.status == "Running":
				return

		for result in self.results:
			if result.status == "Pending":
				record = result
				break
		if record:
			restore_record: PhysicalBackupRestoration = frappe.get_doc(
				"Physical Backup Restoration", record.restore_record
			)
			restore_record.execute()
			record.status = "Running"
			record.save()
		else:
			self.completed = True
			self.save()
			frappe.throw("No pending restoration found")

	@frappe.whitelist()
	def sync(self):
		for result in self.results:
			result.save()

	@frappe.whitelist()
	def reset_failed_restorations(self):
		for result in self.results:
			if result.status == "Failure":
				result.status = "Pending"
				# find the backup from the previous restoration
				site_backup = frappe.db.get_value(
					"Physical Backup Restoration", result.restore_record, "site_backup"
				)
				result.restore_record = self._create_restoration_record(site_backup).name
				result.duration = None
				result.save()


def trigger_next_restoration(record_id: str):
	if not frappe.db.exists("Physical Restoration Test", record_id):
		return
	record: PhysicalRestorationTest = frappe.get_doc("Physical Restoration Test", record_id)
	try:
		record.start()
	except Exception:
		frappe.log_error("Physical Restoration Test Exception")
