from __future__ import annotations

# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
import frappe


@frappe.whitelist()
def all():
	return frappe.get_all("Payment", fields=["name"], filters={"user": frappe.session.user})
