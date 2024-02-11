# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReleaseGroupVariable(Document):
	dashboard_fields = ["key", "value"]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		Config = frappe.qb.DocType("Release Group Variable")
		query = query.where(Config.internal == 0).orderby(Config.key, order=frappe.qb.asc)
		configs = query.run(as_dict=True)
		return configs