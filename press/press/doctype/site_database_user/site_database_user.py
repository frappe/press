# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SiteDatabaseUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site_database_table_permission.site_database_table_permission import (
			SiteDatabaseTablePermission,
		)

		mode: DF.Literal["read_only", "read_write", "granular"]
		password: DF.Password
		permissions: DF.Table[SiteDatabaseTablePermission]
		site: DF.Link
		username: DF.Data
	# end: auto-generated types

	pass
