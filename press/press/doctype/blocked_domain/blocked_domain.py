# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BlockedDomain(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		block_for_all: DF.Check
		root_domain: DF.Link | None
	# end: auto-generated types

	pass
