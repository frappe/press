# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
import json

import frappe
from frappe.model.document import Document

from press.press.doctype.release_group.release_group import ReleaseGroup
from press.utils import log_error


class BenchUpdate(Document):
	def validate(self):
		if not self.is_new():
			return

		self.validate_pending_updates()
		self.validate_pending_site_updates()

	def validate_pending_updates(self):
		if frappe.db.exists(
			"Bench Update", {"status": ("in", ("Pending", "Running")), "group": self.group}
		):
			frappe.throw("An update is already pending for this bench", frappe.ValidationError)

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

	def deploy(self, apps_to_ignore):
		if isinstance(apps_to_ignore, str):
			apps_to_ignore = json.loads(self.apps_to_ignore)

		rg: ReleaseGroup = frappe.get_doc("Release Group", self.group)
		candidate = rg.create_deploy_candidate(apps_to_ignore)
		candidate.build_and_deploy()

		self.status = "Running"
		self.candidate = candidate.name
		self.save()

	def update_sites_on_server(self, server):
		for site in self.sites:
			if site.server == server and site.status == "Pending" and not site.site_update:
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
