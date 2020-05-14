# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class SiteActivity(Document):
	pass


def log_site_activity(site, action, reason=None):
	return frappe.get_doc(
		{"doctype": "Site Activity", "site": site, "action": action, "reason": reason}
	).insert()
