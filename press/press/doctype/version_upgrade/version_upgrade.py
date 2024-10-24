# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.press.doctype.press_notification.press_notification import (
	create_new_notification,
)
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site


class VersionUpgrade(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		destination_group: DF.Link
		last_output: DF.Code | None
		last_traceback: DF.Code | None
		scheduled_time: DF.Datetime | None
		site: DF.Link
		site_update: DF.Link | None
		skip_backups: DF.Check
		skip_failing_patches: DF.Check
		source_group: DF.Link | None
		status: DF.Literal["Scheduled", "Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	doctype = "Version Upgrade"

	def validate(self):
		if self.status == "Failure":
			return
		self.validate_versions()
		self.validate_same_server()
		self.validate_apps()

	def validate_same_server(self):
		site_server = frappe.get_doc("Site", self.site).server
		destination_servers = [
			server.server for server in frappe.get_doc("Release Group", self.destination_group).servers
		]

		if site_server not in destination_servers:
			frappe.throw(
				f"Destination Group {self.destination_group} is not deployed on the site server {site_server}.",
				frappe.ValidationError,
			)

	def validate_apps(self):
		site_apps = [app.app for app in frappe.get_doc("Site", self.site).apps]
		bench_apps = [app.app for app in frappe.get_doc("Release Group", self.destination_group).apps]
		if diff := set(site_apps) - set(bench_apps):
			frappe.throw(
				f"Destination Group {self.destination_group} doesn't have some of the apps installed on {self.site}: {', '.join(diff)}",
				frappe.ValidationError,
			)

	def validate_versions(self):
		source_version = frappe.get_value("Release Group", self.source_group, "version")
		dest_version = frappe.get_value("Release Group", self.destination_group, "version")
		if dest_version == "Nightly":
			frappe.msgprint(
				"You are upgrading the site to Nightly Branch. Please note that Nightly might not be stable"
			)
			return
		if source_version == "Nightly":
			frappe.throw(
				f"Downgrading from Nightly to {dest_version.title()} is not allowed",
				frappe.ValidationError,
			)
		source = int(source_version.split()[1])
		dest = int(dest_version.split()[1])
		if dest - source > 1:
			frappe.throw(
				f"Upgrading Sites by skipping a major version is unsupported. Destination Release Group {self.destination_group} Version is {dest_version.title()} and Source Version is {source_version.title()}",
				frappe.ValidationError,
			)

	@frappe.whitelist()
	def start(self):
		site: "Site" = frappe.get_doc("Site", self.site)
		if site.status.endswith("ing"):
			frappe.throw("Site is under maintenance. Cannot Update")
		try:
			self.site_update = site.move_to_group(
				self.destination_group, self.skip_failing_patches, self.skip_backups
			).name
		except Exception as e:
			frappe.db.rollback()
			self.status = "Failure"
			self.add_comment(text=str(e))

			site = frappe.get_doc("Site", self.site)
			next_version = frappe.get_value("Release Group", self.destination_group, "version")

			message = f"Version Upgrade for site <b>{site.host_name}</b> to <b>{next_version}</b> failed"
			agent_job_id = frappe.get_value("Site Update", self.site_update, "update_job")

			create_new_notification(
				site.team,
				"Version Upgrade",
				"Agent Job",
				agent_job_id,
				message,
			)
		else:
			self.status = frappe.db.get_value("Site Update", self.site_update, "status")
			if self.status == "Success":
				site = frappe.get_doc("Site", self.site)
				next_version = frappe.get_value("Release Group", self.destination_group, "version")

				message = f"Version Upgrade for site <b>{site.host_name}</b> to <b>{next_version}</b> was done successfully"
				agent_job_id = frappe.get_value("Site Update", self.site_update, "update_job")

				create_new_notification(
					site.team,
					"Version Upgrade",
					"Agent Job",
					agent_job_id,
					message,
				)
		self.save()

	@classmethod
	def get_all_scheduled_before_now(cls) -> list["VersionUpgrade"]:
		upgrades = frappe.get_all(
			cls.doctype,
			{"scheduled_time": ("<=", frappe.utils.now()), "status": "Scheduled"},
			pluck="name",
		)

		return cls.get_docs(upgrades)

	@classmethod
	def get_all_ongoing_version_upgrades(cls) -> list[Document]:
		upgrades = frappe.get_all(cls.doctype, {"status": ("in", ["Pending", "Running"])})
		return cls.get_docs(upgrades)

	@classmethod
	def get_docs(cls, names: list[str]) -> list[Document]:
		return [frappe.get_doc(cls.doctype, name) for name in names]


def update_from_site_update():
	ongoing_version_upgrades = VersionUpgrade.get_all_ongoing_version_upgrades()
	for version_upgrade in ongoing_version_upgrades:
		try:
			site_update = frappe.get_doc("Site Update", version_upgrade.site_update)
			version_upgrade.status = site_update.status
			if site_update.status in ["Failure", "Recovered", "Fatal"]:
				last_traceback = frappe.get_value("Agent Job", site_update.update_job, "traceback")
				last_output = frappe.get_value("Agent Job", site_update.update_job, "output")
				version_upgrade.last_traceback = last_traceback
				version_upgrade.last_output = last_output
				version_upgrade.status = "Failure"
				site = frappe.get_doc("Site", version_upgrade.site)
				recipient = site.notify_email or frappe.get_doc("Team", site.team).user

				frappe.sendmail(
					recipients=[recipient],
					subject=f"Automated Version Upgrade Failed for {version_upgrade.site}",
					reference_doctype="Version Upgrade",
					reference_name=version_upgrade.name,
					template="version_upgrade_failed",
					args={
						"site": version_upgrade.site,
						"traceback": last_traceback,
						"output": last_output,
					},
				)
			version_upgrade.save()
			frappe.db.commit()
		except Exception:
			frappe.log_error(f"Error while updating Version Upgrade {version_upgrade.name}")
			frappe.db.rollback()


def run_scheduled_upgrades():
	for upgrade in VersionUpgrade.get_all_scheduled_before_now():
		try:
			site_status = frappe.db.get_value("Site", upgrade.site, "status")
			if site_status.endswith("ing"):
				# If we attempt to start the upgrade now, it will fail
				# This will be picked up in the next iteration
				continue
			upgrade.start()
			frappe.db.commit()
		except Exception:
			log_error("Scheduled Version Upgrade Error", upgrade=upgrade)
			frappe.db.rollback()
