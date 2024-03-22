# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DeployCandidateDependency(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dependency: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		version: DF.Data
	# end: auto-generated types

	pass
