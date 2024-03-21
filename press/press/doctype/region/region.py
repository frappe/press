# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class Region(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		last_allocated_to: DF.Link | None
		region_name: DF.Data
	# end: auto-generated types

	pass
