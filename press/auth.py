# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe


def hook():
	if frappe.form_dict.cmd:
		path = f"/api/request/{frappe.form_dict.cmd}"
	else:
		path = frappe.request.path

	data = {
		"timestamp": frappe.utils.now(),
		"user_type": frappe.session.data.user_type,
		"path": path,
		"user": frappe.session.data.user,
	}
