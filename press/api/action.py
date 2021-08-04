# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def get(name):
	action = frappe.get_doc("UI Action", name)
	if not action.is_authorized():
		return
	return action


@frappe.whitelist()
def execute(name, **kwargs):
	kwargs.pop("cmd")
	action = frappe.get_doc("UI Action", name)
	return action.execute(**kwargs)
