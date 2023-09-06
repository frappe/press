# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressMethodPermission(Document):
	pass


def available_actions():
	result = {}
	doctypes = frappe.get_all(
		"Press Method Permission", pluck="document_type", distinct=True
	)

	for doctype in doctypes:
		result[doctype] = {
			perm["checkbox_label"]: perm["method"]
			for perm in frappe.get_all(
				"Press Method Permission", {"document_type": doctype}, ["checkbox_label", "method"]
			)
		}

	return result
