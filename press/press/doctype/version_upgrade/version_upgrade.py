# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from typing import List

import frappe
from frappe.model.document import Document


class VersionUpgrade(Document):
	doctype = "Version Upgrade"

	def validate(self):
		self.validate_same_server()
		self.validate_apps()

	def validate_same_server(self):
		site_server = frappe.get_doc("Site", self.site).server
		destination_servers = [
			server.server
			for server in frappe.get_doc("Release Group", self.destination_group).servers
		]

		if site_server not in destination_servers:
			frappe.throw(
				f"Destination Group {self.destination_group} is not deployed on the site server {site_server}.",
				frappe.ValidationError,
			)

	def validate_apps(self):
		site_apps = [app.app for app in frappe.get_doc("Site", self.site).apps]
		bench_apps = [
			app.app for app in frappe.get_doc("Release Group", self.destination_group).apps
		]
		if set(site_apps) - set(bench_apps):
			frappe.throw(
				f"Destination Release Group {self.destination_group} doesn't have some of the apps installed on {self.site}",
				frappe.ValidationError,
			)

	@frappe.whitelist()
	def start(self):
		site = frappe.get_doc("Site", self.site)
		if site.status.endswith("ing"):
			frappe.throw("Site is under maintenance. Cannot Update")
		try:
			self.site_update = site.move_to_group(
				self.destination_group, self.skip_failing_patches
			).name
		except Exception as e:
			frappe.db.rollback()
			self.status = "Failure"
			self.add_comment(text=str(e))
		else:
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
			last_traceback = frappe.get_value("Agent Job", site_update.update_job, "traceback")
			last_output = frappe.get_value("Agent Job", site_update.update_job, "output")
			version_upgrade.last_traceback = last_traceback
			version_upgrade.last_output = last_output
			version_upgrade.status = "Failure"
			recipient = frappe.db.get_value("Site", version_upgrade.site, "notify_email")
			msg = f"""
			Automated Version Upgrade has failed. Please resolve the issue and retry for upgrade.
			Site: {version_upgrade.site}
			Traceback: ```{last_traceback}```
			Output: ```{last_output}```
			"""
			frappe.sendmail(
				recipient=[recipient],
				subject="Automated Version Upgrade Failed",
				message=msg,
				as_markdown=True,
				reference_doctype="Version Upgrade",
				reference_name=version_upgrade.name,
			)
		version_upgrade.save()


def run_scheduled_upgrades():
	for upgrade in VersionUpgrade.get_all_scheduled_before_now():
		upgrade.start()
