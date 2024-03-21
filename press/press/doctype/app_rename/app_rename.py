# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AppRename(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		before_migrate_script: DF.Code
		new_name: DF.Link
		old_name: DF.Data
		rollback_script: DF.Code | None
	# end: auto-generated types

	pass
