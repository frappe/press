# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.agent import Agent


class PhysicalBackupGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.physical_backup_group_site.physical_backup_group_site import (
			PhysicalBackupGroupSite,
		)

		available_backups: DF.Int
		no_of_sites: DF.Int
		site_backups: DF.Table[PhysicalBackupGroupSite]
		successful_backups: DF.Int
		unavailable_backups: DF.Int
	# end: auto-generated types

	@property
	def next_site_backup(self) -> PhysicalBackupGroupSite | None:
		# Fetch the last one before pending
		for site in self.site_backups:
			if site.status == "Pending":
				return site
		return None

	@property
	def current_site_backup(self) -> PhysicalBackupGroupSite | None:
		# Fetch the last one before pending
		for site in reversed(self.site_backups):
			if site.status != "Pending":
				return site
		return None

	@frappe.whitelist()
	def sync(self):
		self.no_of_sites = len(self.site_backups)
		# Check site backup's status
		for site in self.site_backups:
			site.sync()
		self.successful_backups = len([site for site in self.site_backups if site.status == "Success"])
		self.available_backups = len([site for site in self.site_backups if site.backup_available])
		self.unavailable_backups = len(
			[site for site in self.site_backups if (not site.backup_available and site.status == "Success")]
		)
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def set_db_sizes(self):
		for site in self.site_backups:
			site.set_db_size()

	@frappe.whitelist()
	def trigger_next_backup(self):
		frappe.enqueue_doc(self.doctype, self.name, "_trigger_next_backup", queue="default", at_front=True)
		frappe.msgprint("Triggered next backup")

	def _trigger_next_backup(self):
		current_site_backup = self.current_site_backup
		if current_site_backup and current_site_backup.status == "Running":
			return

		next_site_backup = self.next_site_backup
		if not next_site_backup:
			frappe.msgprint("No more sites to backup")
			return
		next_site_backup.status = "Running"
		next_site_backup.save(ignore_permissions=True)
		frappe.enqueue_doc(
			"Physical Backup Group Site",
			next_site_backup.name,
			"physical_backup",
			queue="default",
			enqueue_after_commit=True,
		)

	@frappe.whitelist()
	def retry_failed_backups(self):
		for site in self.site_backups:
			if site.status == "Failure":
				site.backup = None
				site.backup_available = False
				site.status = "Pending"
				site.save(ignore_permissions=True)

	@frappe.whitelist()
	def delete_backups(self):
		for site in self.site_backups:
			site.delete_backup()

	@frappe.whitelist()
	def activate_all_sites(self):
		for site_backup in self.site_backups:
			site = frappe.get_doc("Site", site_backup.site)
			agent = Agent(site.server)
			agent.activate_site(site)

	@frappe.whitelist()
	def create_duplicate_group(self):
		suffix = 2
		name = self.name + "-" + str(suffix)
		while frappe.db.exists("Physical Backup Group", name):
			suffix += 1
			name = self.name + "-" + str(suffix)
		duplicate_group = frappe.get_doc(
			{
				"doctype": "Physical Backup Group",
				"name": name,
				"site_backups": [
					{"site": site_backup.site, "status": "Pending"} for site_backup in self.site_backups
				],
			}
		).insert()
		frappe.msgprint("Created duplicate group - " + duplicate_group.name)
