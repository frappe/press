# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class VirtualMachineImageVolume(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		device: DF.Data | None
		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		size: DF.Int
		snapshot_id: DF.Data | None
		volume_type: DF.Literal["gp3", "gp2"]
	# end: auto-generated types

	pass
