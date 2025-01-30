from __future__ import annotations

# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
# import frappe
from frappe.model.document import Document


class PhysicalBackupFileMetadata(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checksum: DF.Data | None
		file: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		size: DF.Int
	# end: auto-generated types

	pass
