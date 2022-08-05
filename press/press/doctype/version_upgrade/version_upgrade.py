# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from typing import List

import frappe
from frappe.model.document import Document


class VersionUpgrade(Document):
	doctype = "Version Upgrade"

	def after_insert(self):
		if not self.scheduled_time:
			self.start()

	@frappe.whitelist()
	def start(self):
		site = frappe.get_doc("Site", self.site)
		if site.status.endswith("ing"):
			frappe.throw("Site is under maintenance. Cannot Update")
		self.site_update = site.move_to_group(
			self.destination_group, self.skip_failing_patches
		).name
		self.status = frappe.db.get_value("Site Update", self.site_update, "status")
		self.save()

	@classmethod
	def get_all_scheduled_before_now(cls) -> List[Document]:
		upgrades = frappe.get_all(
			cls.doctype,
			{"scheduled_time": ("<=", frappe.utils.now()), "status": "Scheduled"},
			pluck="name",
		)

		return cls.get_docs(upgrades)

	@classmethod
	def get_all_ongoing_version_upgrades(cls) -> List[Document]:
		upgrades = frappe.get_all(cls.doctype, {"status": ("in", ["Pending", "Running"])})
		return cls.get_docs(upgrades)

	@classmethod
	def get_docs(cls, names: List[str]) -> List[Document]:
		return [frappe.get_doc(cls.doctype, name) for name in names]


def update_from_site_update():
	ongoing_version_upgrades = VersionUpgrade.get_all_ongoing_version_upgrades()
	for version_upgrade in ongoing_version_upgrades:
		site_update = frappe.get_doc("Site Update", version_upgrade.site_update)
		version_upgrade.status = site_update.status
		if site_update.status in ["Failure", "Recovered", "Fatal"]:
			version_upgrade.last_traceback = frappe.get_value(
				"Agent Job", site_update.update_job, "traceback"
			)
			version_upgrade.last_output = frappe.get_value(
				"Agent Job", site_update.update_job, "output"
			)
			version_upgrade.status = "Failure"
		version_upgrade.save()


def run_scheduled_upgrades():
	for upgrade in VersionUpgrade.get_all_scheduled_before_now():
		upgrade.start()
