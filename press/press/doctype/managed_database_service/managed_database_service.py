# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ManagedDatabaseService(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		database_host: DF.Data
		database_root_user: DF.Data
		port: DF.Data | None
		root_user_password: DF.Password
		service_provider: DF.Literal["AWS RDS"]
		team: DF.Link
	# end: auto-generated types

	pass
