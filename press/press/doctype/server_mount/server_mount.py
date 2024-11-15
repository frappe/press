# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class ServerMount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		filesystem: DF.Literal["ext4", "none"]
		mount_options: DF.Data | None
		mount_point: DF.Data
		mount_point_group: DF.Data
		mount_point_mode: DF.Data
		mount_point_owner: DF.Data
		mount_type: DF.Literal["Volume", "Bind"]
		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		source: DF.Data
		status: DF.Literal["Pending", "Success", "Failure"]
		uuid: DF.Data | None
		volume_id: DF.Data | None
	# end: auto-generated types

	pass
