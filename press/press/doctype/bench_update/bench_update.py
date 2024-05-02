# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.press.doctype.release_group.release_group import ReleaseGroup
from press.utils import log_error


class BenchUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.bench_site_update.bench_site_update import BenchSiteUpdate
		from press.press.doctype.bench_update_app.bench_update_app import BenchUpdateApp

		apps: DF.Table[BenchUpdateApp]
		candidate: DF.Link | None
		group: DF.Link
		sites: DF.Table[BenchSiteUpdate]
		status: DF.Literal["Pending", "Running", "Build Successful", "Failure", "Success"]
	# end: auto-generated types

	def validate(self):
		if not self.is_new():
			return

		self.validate_pending_updates()
		self.validate_pending_site_updates()

	def validate_pending_updates(self):
		if frappe.get_doc("Release Group", self.group).deploy_in_progress:
			frappe.throw(
				"A deploy for this bench is already in progress", frappe.ValidationError
			)

	def validate_pending_site_updates(self):
		for site in self.sites:
			if frappe.db.exists(
				"Site Update",
				{"site": site.site, "status": ("in", ("Pending", "Running"))},
			):
				frappe.throw("An update is already pending for this site", frappe.ValidationError)

	def deploy(self):
		rg: ReleaseGroup = frappe.get_doc("Release Group", self.group)
		candidate = rg.create_deploy_candidate(self.apps)
		candidate.deploy_to_production()

		self.status = "Running"
		self.candidate = candidate.name
		self.save()
		return candidate.name

	def update_sites_on_server(self, bench, server):
		if frappe.get_value("Bench", bench, "status") != "Active":
			return

		for site in self.sites:
			if site.server != server:
				continue

			# Don't try to update if the site is already on another bench
			# It already could be on newest bench and Site Update couldn't be scheduled
			# In any case our job was to move site to a newer than this, which is already done
			current_site_bench = frappe.get_value("Site", site.site, "bench")
			if site.source_candidate != frappe.get_value(
				"Bench", current_site_bench, "candidate"
			):
				site.status = "Success"
				self.save(ignore_permissions=True)
				frappe.db.commit()
				continue

			if site.status == "Pending" and not site.site_update:
				try:
					if frappe.get_all(
						"Site Update",
						{"site": site.site, "status": ("in", ("Pending", "Running", "Failure"))},
						ignore_ifnull=True,
						limit=1,
					):
						continue
					site_update = frappe.get_doc("Site", site.site).schedule_update(
						skip_failing_patches=site.skip_failing_patches, skip_backups=site.skip_backups
					)
					site.site_update = site_update
					self.save(ignore_permissions=True)
					frappe.db.commit()
				except Exception as e:
					log_error("Bench Update: Failed to create Site Update", exception=e)
					frappe.db.rollback()
					site.status = "Failure"
					self.save(ignore_permissions=True)
					traceback = frappe.get_traceback(with_context=True)
					comment = f"Failed to schedule update for {site.site} <br><br><pre><code>{traceback}</pre></code>"
					self.add_comment(text=comment)
					frappe.db.commit()
