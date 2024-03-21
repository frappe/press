# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VirtualMachineVolume(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		iops: DF.Int
		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		size: DF.Int
		throughput: DF.Int
		volume_id: DF.Data | None
		volume_type: DF.Literal["gp3", "gp2"]
	# end: auto-generated types

	pass
