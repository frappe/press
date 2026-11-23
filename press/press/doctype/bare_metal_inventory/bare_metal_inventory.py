# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BareMetalInventory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bmc_ip_address: DF.Data | None
		bmc_password: DF.Password | None
		bmc_user: DF.Data | None
		private_ip_address: DF.Data | None
		public_ip_address: DF.Data
		root_password: DF.Password | None
		root_user: DF.Data | None
	# end: auto-generated types

	pass
