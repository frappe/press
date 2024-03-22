# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressMethodPermission(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checkbox_label: DF.Data
		document_type: DF.Link
		method: DF.Data
	# end: auto-generated types

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
