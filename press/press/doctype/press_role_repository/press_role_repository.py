# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PressRoleRepository(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		github_installation: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		repository: DF.Data
	# end: auto-generated types

	pass
