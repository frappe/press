# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document

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

	@dashboard_whitelist()
	def mark_as_addressed(self):
		self.read = True
		self.is_addressed = True
		self.save()
		frappe.db.commit()

	@dashboard_whitelist()
	def mark_as_read(self):
		self.db_set("read", True)


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
