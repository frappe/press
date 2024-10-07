# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist


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
			"Downtime/Performance",
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

	def after_insert(self):
		if frappe.local.dev_server:
			return

		user = frappe.db.get_value("Team", self.team, "user")
		if user == "Administrator":
			return

		if self.type == "Bench Deploy":
			self.send_bench_deploy_failed(user)

	def send_bench_deploy_failed(self, user: str):
		group_name = frappe.db.get_value("Deploy Candidate", self.document_name, "group")
		rg_title = frappe.db.get_value("Release Group", group_name, "title")

		frappe.sendmail(
			recipients=[user],
			subject=f"Bench Deploy Failed - {rg_title}",
			template="bench_deploy_failure",
			args={
				"message": self.title,
				"link": f"dashboard/groups/{group_name}/deploys/{self.document_name}",
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
		if document_type == "Agent Job":
			reference_doctype = "Site"
			reference_doc = frappe.db.get_value("Agent Job", document_name, "site")
			if not reference_doc:
				reference_doctype = "Server"
				reference_doc = frappe.db.get_value("Agent Job", document_name, "server")
		elif document_type == "Deploy Candidate":
			reference_doctype = "Release Group"
			reference_doc = frappe.db.get_value("Deploy Candidate", document_name, "group")

		frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": team,
				"type": type,
				"document_type": document_type,
				"document_name": document_name or 0,
				"message": message,
				"reference_doctype": reference_doctype,
				"reference_name": reference_doc,
			}
		).insert()
		frappe.publish_realtime("press_notification", doctype="Press Notification", message={"team": team})
