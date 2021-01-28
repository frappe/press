# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Bench")
	rename_field("Bench", "workers", "background_workers")
