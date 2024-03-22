# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class BenchApp(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		hash: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		release: DF.Link
		source: DF.Link
	# end: auto-generated types

	pass
