# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.press.doctype.release_group.release_group import ReleaseGroup


class BenchUpdate(Document):
	def validate(self):
		if not self.is_new():
			return

		self.validate_pending_updates()
		self.validate_pending_site_updates()

	def validate_ongoing_updates(self):
		if frappe.db.exists(
			"Bench Update", {"status": ("in", ("Pending", "Running", "Failure"))}
		):
			frappe.throw("An update is already pending for this bench", frappe.ValidationError)

		if frappe.get_doc("Release Group", self.group).deploy_in_progress:
			frappe.throw("A deploy for this bench is already in progress")

	def validate_pending_site_updates(self):
		for site in self.sites:
			if frappe.db.exists(
				"Site Update",
				{"site": site.site, "status": ("in", ("Pending", "Running", "Failure"))},
			):
				frappe.throw("An update is already pending for this site", frappe.ValidationError)

	def after_insert(self):
		rg: ReleaseGroup = frappe.get_doc("Release Group", self.group)
		candidate = rg.create_deploy_candidate(self.apps_to_ignore, bench_update=self.name)
		candidate.build_and_deploy()

		self.status = "Running"
