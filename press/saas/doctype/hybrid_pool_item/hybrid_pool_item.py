# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

# import frappe
from frappe.model.document import Document


class HybridPoolItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		custom_pool_size: DF.Int
		field: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		preferred_cluster: DF.Link | None
		value: DF.Data
	# end: auto-generated types

	pass
