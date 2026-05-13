# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.set_value("Product Trial Request", {"is_subscription_created": 0}, "is_subscription_created", 1)
