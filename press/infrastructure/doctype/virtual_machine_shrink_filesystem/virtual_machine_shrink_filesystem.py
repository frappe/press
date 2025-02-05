# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class VirtualMachineShrinkFilesystem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available: DF.Int
		device_name: DF.Data | None
		mount_point: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		service: DF.Data | None
		size: DF.Int
		type: DF.Data
		uuid: DF.Data
		volume_id: DF.Data
	# end: auto-generated types

	pass
