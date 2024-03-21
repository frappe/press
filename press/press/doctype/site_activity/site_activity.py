# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


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
			"Enable Database Access",
			"Disable Database Access",
		]
		reason: DF.SmallText | None
		site: DF.Link
	# end: auto-generated types

	dashboard_fields = ["action", "reason", "site"]

	def after_insert(self):
		if self.action == "Login as Administrator" and self.reason:
			d = frappe.get_all("Site", {"name": self.site}, ["notify_email", "team"])[0]
			recipient = d.notify_email or frappe.get_doc("Team", d.team).user
			if recipient:
				team = frappe.get_doc("Team", d.team)
				team.notify_with_email(
					[recipient],
					subject="Administrator login to your site",
					template="admin_login",
					args={"site": self.site, "user": self.owner, "reason": self.reason},
					reference_doctype=self.doctype,
					reference_name=self.name,
				)


def log_site_activity(site, action, reason=None):
	return frappe.get_doc(
		{"doctype": "Site Activity", "site": site, "action": action, "reason": reason}
	).insert()
