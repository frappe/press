from __future__ import annotations

import contextlib

# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
import pymysql


def execute():
	with contextlib.suppress(pymysql.err.OperationalError):
		frappe.db.sql("UPDATE `tabMarketplace App` SET show_for_site_creation = show_for_first_site_creation")
