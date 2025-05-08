# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MariaDBBinlog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		database_server: DF.Link
		file_creation_time: DF.Datetime
		file_modification_time: DF.Datetime
		indexed: DF.Check
		purged_from_disk: DF.Check
		size_mb: DF.Float
	# end: auto-generated types

	pass
