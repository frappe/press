# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.press_notification.press_notification import (
	create_new_notification,
)
from press.press.doctype.site.site import TRANSITORY_STATES
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site


class VersionUpgrade(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench_deploy_successful: DF.Check
		deploy_private_bench: DF.Check
		destination_group: DF.Link
		last_output: DF.Code | None
		last_traceback: DF.Code | None
		scheduled_time: DF.Datetime | None
		site: DF.Link
		site_update: DF.Link | None
		skip_backups: DF.Check
		skip_failing_patches: DF.Check
		source_group: DF.Link | None
		status: DF.Literal["Scheduled", "Pending", "Running", "Success", "Failure", "Cancelled"]
	# end: auto-generated types

	doctype = "Version Upgrade"

	def validate(self):
		if self.status == "Failure":
			return
		self.validate_versions()
		# Skip server validation if waiting for bench deploy
		if not self.deploy_private_bench or self.bench_deploy_successful:
			self.validate_same_server()
		self.validate_apps()

	def after_insert(self):
		if self.deploy_private_bench and self.destination_group:
			self.status = "Pending"
			self.save()
			frappe.get_doc("Release Group", self.destination_group).initial_deploy()

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
		if site.status in TRANSITORY_STATES:
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
			site_update_status = frappe.db.get_value("Site Update", self.site_update, "status")
			if site_update_status in ["Failure", "Recovered", "Fatal"]:
				self.status = "Failure"
				self.send_version_upgrade_failure_email(agent_job=self.site_update)
			else:
				self.status = site_update_status
			if self.status == "Success":
				site = frappe.get_doc("Site", self.site)
				next_version = frappe.get_value("Release Group", self.destination_group, "version")

				message = f"Version Upgrade for site <b>{site.host_name}</b> to <b>{next_version}</b> has completed successfully"
				agent_job_id = frappe.get_value("Site Update", self.site_update, "update_job")

				create_new_notification(
					site.team,
					"Version Upgrade",
					"Agent Job",
					agent_job_id,
					message,
				)
		self.save()

	def update_version_upgrade_on_process_job(self, job):
		"""Handles agent job updates when new bench deploy is involved for site version upgrade"""
		if job.job_type != "New Bench":
			return

		if job.status == "Success":
			self.bench_deploy_successful = 1
			if self.scheduled_time:
				self.status = "Scheduled"
				self.save()
			else:
				self.start()
		elif job.status in ["Failure", "Delivery Failure"]:
			self.status = "Cancelled"
			self.send_version_upgrade_failure_email(agent_job=job.name, bench_deploy_failure=True)
			self.save()

	def send_version_upgrade_failure_email(self, agent_job: str, bench_deploy_failure: bool = False) -> None:
		# Set failure traceback and send email to inform user
		traceback, output = frappe.get_value("Agent Job", agent_job, ["traceback", "output"])
		self.last_traceback = traceback
		self.last_output = output

		recipients = get_communication_info("Email", "Site Activity", "Site", self.site)
		if not recipients:
			return

		subject = f"Automated Version Upgrade Failed for {self.site}"
		content = frappe.render_template(
			"press/templates/emails/version_upgrade_failed.html",
			{
				"site": self.site,
				"traceback": traceback,
				"output": output,
				"bench_deploy_failure": bench_deploy_failure,
			},
			is_path=True,
		)
		communication = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "Email",
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"subject": subject,
				"content": content,
				"is_notification": True,
				"recipients": ", ".join(recipients),
			}
		)
		communication.insert(ignore_permissions=True)
		communication.send_email()

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
			if not version_upgrade.site_update:
				continue
			site_update_status, site_update_job = frappe.db.get_value(
				"Site Update",
				version_upgrade.site_update,
				["status", "update_job"],
			)
			version_upgrade.status = site_update_status
			if site_update_status in ["Failure", "Recovered", "Fatal"]:
				version_upgrade.status = "Failure"
				version_upgrade.send_version_upgrade_failure_email(agent_job=site_update_job)
			version_upgrade.save()
			frappe.db.commit()
		except Exception:
			frappe.log_error(f"Error while updating Version Upgrade {version_upgrade.name}")
			frappe.db.rollback()


def run_scheduled_upgrades():
	for upgrade in VersionUpgrade.get_all_scheduled_before_now():
		try:
			site_status = frappe.db.get_value("Site", upgrade.site, "status")
			if site_status == "Archived":
				frappe.db.set_value("Version Upgrade", upgrade.name, "status", "Cancelled")
				continue
			if site_status in TRANSITORY_STATES:
				# If we attempt to start the upgrade now, it will fail
				# This will be picked up in the next iteration
				continue

			if upgrade.deploy_private_bench and not upgrade.bench_deploy_successful:
				continue
			upgrade.start()
			frappe.db.commit()
		except Exception:
			log_error("Scheduled Version Upgrade Error", upgrade=upgrade)
			frappe.db.rollback()
