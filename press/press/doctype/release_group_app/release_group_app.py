# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from press.api.bench import apps


class ReleaseGroupApp(Document):
	dashboard_fields = ["app"]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		group = cstr(filters.get("parent", "")) if filters else None
		return apps(group)
