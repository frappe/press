# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.press.doctype.communication_info.communication_info import get_communication_info


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

		if self.action == "Login as Administrator" and self.reason:
			recipients = get_communication_info("Email", "Site Activity", "Site", self.site)
			if recipients:
				frappe.sendmail(
					recipients=recipients,
					subject="Administrator login to your site",
					template="admin_login",
					args={"site": self.site, "user": self.owner, "reason": self.reason},
					reference_doctype=self.doctype,
					reference_name=self.name,
				)

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


def log_site_activity(site, action, reason=None, job=None):
	return frappe.get_doc(
		{"doctype": "Site Activity", "site": site, "action": action, "reason": reason, "job": job}
	).insert()
