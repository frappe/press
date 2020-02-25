# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SiteHistory(Document):
	pass

def log_site_history(site, action):
	return frappe.get_doc({"doctype": "Site History", "site": site, "action": action}).insert()

