# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReleaseGroupVariable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING, ClassVar

	if TYPE_CHECKING:
		from frappe.types import DF

		internal: DF.Check
		key: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		value: DF.Text
	# end: auto-generated types

	dashboard_fields: ClassVar = ["key", "value"]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		environmentVariable = frappe.qb.DocType("Release Group Variable")
		query = query.where(environmentVariable.internal == 0).orderby(
			environmentVariable.key, order=frappe.qb.asc
		)
		return query.run(as_dict=True)
