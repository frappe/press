# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VirtualMachineMigration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)
		from press.infrastructure.doctype.virtual_machine_migration_volume.virtual_machine_migration_volume import (
			VirtualMachineMigrationVolume,
		)

		copied_virtual_machine: DF.Link | None
		instance_type: DF.Data
		status: DF.Literal["Draft", "Running", "Success", "Failure"]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_machine: DF.Link
		virtual_machine_image: DF.Link
		volumes: DF.Table[VirtualMachineMigrationVolume]
	# end: auto-generated types

	pass
