# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReleaseGroupVariable(Document):
	dashboard_fields = ["key", "value"]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		environmentVariable = frappe.qb.DocType("Release Group Variable")
		query = query.where(environmentVariable.internal == 0).orderby(
			environmentVariable.key, order=frappe.qb.asc
		)
		configs = query.run(as_dict=True)
		return configs
