# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class VirtualMachineMigrationMount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		service: DF.Data | None
		source_mount_point: DF.Data | None
		target_mount_point: DF.Data | None
		uuid: DF.Data | None
	# end: auto-generated types

	pass
