# -*- coding: utf-8 -*-  # noqa: UP009
# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
import frappe


def execute():
	frappe.db.set_value("Server", {"status": "Active"}, "set_bench_memory_limits", True, debug=True)
