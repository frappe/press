# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class SiteActivity(Document):
	def after_insert(self):
		if self.action == "Login as Administrator" and self.reason:
			d = frappe.get_all("Site", {"name": self.site}, ["notify_email", "team"])[0]
			recipient = d.notify_email
			if recipient:
				team = frappe.get_doc("Team", d.team)
				team.notify_with_email(
					[recipient],
					subject="Administrator login to your site",
					template="admin_login",
					args={"site": self.site, "user": self.owner, "reason": self.reason},
					reference_doctype=self.doctype,
					reference_name=self.name,
					now=True,
				)


def log_site_activity(site, action, reason=None):
	return frappe.get_doc(
		{"doctype": "Site Activity", "site": site, "action": action, "reason": reason}
	).insert()
