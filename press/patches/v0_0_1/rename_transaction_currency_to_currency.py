# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("press", "doctype", "team")
	rename_field("Team", "transaction_currency", "currency")
