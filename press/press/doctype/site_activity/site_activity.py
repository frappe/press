# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class SiteActivity(Document):
	def after_insert(self):
		if self.action == "Login as Administrator" and self.reason:
			recipient = frappe.db.get_value("Site", self.site, "notify_email")
			if recipient:
					frappe.sendmail(
						recipients=[recipient],
						# TODO: update recipient for email to use custom recipient configured in team <29-09-21, Balamurali M> #
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
