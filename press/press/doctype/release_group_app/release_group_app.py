# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from press.api.bench import apps


class ReleaseGroupApp(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		enable_auto_deploy: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		source: DF.Link
		title: DF.Data
	# end: auto-generated types

	dashboard_fields = ["app"]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		group = cstr(filters.get("parent", "")) if filters else None
		return apps(group)
