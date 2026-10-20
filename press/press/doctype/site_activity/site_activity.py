# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import escape_html

from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.press_notification.press_notification import (
	notify_backup_access,
	notify_resource_access,
)


class SiteActivity(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Literal[
			"Activate Site",
			"Add Domain",
			"Archive",
			"Backup",
			"Create",
			"Clear Cache",
			"Deactivate Site",
			"Install App",
			"Login as Administrator",
			"Migrate",
			"Reinstall",
			"Restore",
			"Suspend Site",
			"Uninstall App",
			"Unsuspend Site",
			"Update",
			"Update Configuration",
			"Drop Offsite Backups",
			"Drop Physical Backups",
			"Enable Database Access",
			"Disable Database Access",
			"Create Database User",
			"Remove Database User",
			"Modify Database User Permissions",
			"Disable Monitoring And Alerts",
			"Enable Monitoring And Alerts",
			"Access Offsite Backups",
			"Authorize Backup Access",
			"Archive Notification",
		]
		job: DF.Link | None
		reason: DF.SmallText | None
		site: DF.Link
		team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ("action", "reason", "site", "job")

	def after_insert(self):
		if self.team == "Administrator":
			return

		if self.action == "Login as Administrator":
			self.notify_admin_login()

		if self.action == "Access Offsite Backups":
			self.notify_backup_access()

		if self.action == "Disable Monitoring And Alerts" and self.reason:
			recipients = get_communication_info("Email", "Site Activity", "Site", self.site)
			if recipients:
				frappe.sendmail(
					recipients=recipients,
					subject="Site Monitoring Disabled",
					template="disabled_site_monitoring",
					args={"site": self.site, "reason": self.reason},
					reference_doctype=self.doctype,
					reference_name=self.name,
				)

	def notify_admin_login(self):
		message = f"{self.owner} logged in to {self.site} as Administrator."
		if self.reason:
			message += f" Reason: {escape_html(self.reason)}"
		title = f"Administrator login to {self.site}"
		notify_resource_access(self, "Site", self.site, title, message)

	def notify_backup_access(self):
		notify_backup_access(self, "Site", self.site, self.site)


def log_site_activity(site, action, reason=None, job=None):
	return frappe.get_doc(
		{"doctype": "Site Activity", "site": site, "action": action, "reason": reason, "job": job}
	).insert()
