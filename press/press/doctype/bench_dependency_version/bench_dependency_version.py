# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BenchDependencyVersion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		supported_frappe_version: DF.Link | None
		version: DF.Data | None
	# end: auto-generated types

	dashboard_fields = ["version", "supported_frappe_version"]
