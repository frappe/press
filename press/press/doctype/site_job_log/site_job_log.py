# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class SiteJobLog(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Site Job Log", ["site", "timestamp"])
