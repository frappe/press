# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from press.api.client import dashboard_whitelist
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.press_notification.reference import find_reference
from press.utils.redact import redact_secrets


class PressNotification(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assistance_url: DF.Data | None
		document_name: DF.DynamicLink
		document_type: DF.Link
		is_actionable: DF.Check
		is_addressed: DF.Check
		message: DF.LongText | None
		read: DF.Check
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		team: DF.Link
		title: DF.SmallText | None
		traceback: DF.Code | None
		type: DF.Literal[
			"Site Update",
			"Site Migrate",
			"Version Upgrade",
			"Bench Deploy",
			"Site Recovery",
			"Agent Job Failure",
			"Downtime/Performance",
			"Support Access",
			"Auto Scale",
			"Malware Scan",
			"Resource Access",
		]
	# end: auto-generated types

	dashboard_fields = (
		"team",
		"document_type",
		"class",
		"type",
		"document_name",
		"is_actionable",
		"read",
		"is_addressed",
		"title",
		"message",
		"traceback",
		"assistance_url",
	)

	def before_insert(self):
		if not self.reference_doctype:
			self.reference_doctype, self.reference_name = find_reference(
				self.document_type, self.document_name
			)

	def validate(self):
		# Teams see the traceback in the dashboard's error dialog
		self.traceback = redact_secrets(self.traceback)

	def after_insert(self):
		if frappe.local.dev_server:
			return

		user = frappe.db.get_value("Team", self.team, "user")
		if user == "Administrator":
			return

		if self.type == "Bench Deploy":
			self.send_bench_deploy_failed(get_communication_info("Email", "General", "Team", self.team))
		elif self.type == "Malware Scan":
			self.send_malware_found(
				get_communication_info("Email", "Server Activity", "Server", self.reference_name)
			)
		elif self.type == "Resource Access":
			self.send_resource_access()

	def send_bench_deploy_failed(self, mails: list[str]):
		"""Skip emails in case of warning"""
		if getattr(self, "class", None) == "Warning":
			return

		group_name = frappe.db.get_value("Deploy Candidate Build", self.document_name, "group")
		rg_title = frappe.db.get_value("Release Group", group_name, "title")

		frappe.sendmail(
			recipients=mails,
			subject=f"Bench Deploy Failed - {rg_title}",
			template="bench_deploy_failure",
			args={
				"message": self.title,
				"link": f"dashboard/groups/{group_name}/deploys/{self.document_name}",
			},
		)

	def send_malware_found(self, mails: list[str]):
		scan = frappe.get_doc("Malware Scan", self.document_name)
		frappe.sendmail(
			recipients=mails,
			subject=self.title,
			template="malware_scan_infected",
			args={
				"server": self.reference_name,
				"files": scan.flagged_files(),
				"link": f"dashboard/servers/{self.reference_name}/security",
			},
		)

	def send_resource_access(self):
		if self.reference_doctype == "Site":
			mails = get_communication_info("Email", "Site Activity", "Site", str(self.reference_name))
		else:
			mails = get_communication_info("Email", "General", "Team", self.team)
		frappe.sendmail(
			recipients=mails,
			subject=str(self.title),
			template="resource_access",
			args={"message": self.message, "link": f"dashboard/{resource_route(self)}"},
		)

	@dashboard_whitelist()
	def mark_as_addressed(self):
		self.read = True
		self.is_addressed = True
		self.save()
		frappe.db.commit()

	@dashboard_whitelist()
	def mark_as_read(self):
		self.db_set("read", True)


def notify_resource_access(
	document: Document,
	reference_doctype: str,
	reference_name: str,
	title: str,
	message: str,
	team: str | None = None,
):
	"""Tell the team that owns `reference_name`, or `team`, that someone got into it."""
	team = team or cstr(frappe.db.get_value(reference_doctype, reference_name, "team"))
	frappe.get_doc(
		{
			"doctype": "Press Notification",
			"team": team,
			"type": "Resource Access",
			"class": "Warning",
			"document_type": document.doctype,
			"document_name": document.name,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"title": title,
			"message": message,
		}
	).insert(ignore_permissions=True)
	frappe.publish_realtime(
		"press_notification", doctype="Press Notification", message={"team": team}, after_commit=True
	)


def resource_route(notification) -> str:
	"""The dashboard page where the team can see the access."""
	if notification.reference_doctype == "Site":
		return f"sites/{notification.reference_name}/activity"
	if notification.reference_doctype == "Server":
		return f"servers/{notification.reference_name}/snapshots"
	return f"groups/{notification.reference_name}"


def notify_backup_access(
	document: Document, reference_doctype: str, reference_name: str, site: str, team: str | None = None
):
	"""Tell the owning team that the session got a download link for a backup of `site`."""
	message = f"{frappe.session.user} got a download link for a backup of {site}."
	title = f"Backup of {site} accessed"
	notify_resource_access(document, reference_doctype, reference_name, title, message, team)


def create_new_notification(team, type, document_type, document_name, message):
	if not frappe.db.exists("Press Notification", {"document_name": document_name}):
		frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": team,
				"type": type,
				"document_type": document_type,
				"document_name": document_name or 0,
				"message": message,
			}
		).insert()
		frappe.publish_realtime("press_notification", doctype="Press Notification", message={"team": team})
