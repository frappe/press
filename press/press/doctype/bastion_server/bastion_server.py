# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BastionServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cluster: DF.Link | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		hostname: DF.Data
		hostname_abbreviation: DF.Data | None
		ip: DF.Data | None
		provider: DF.Literal["Generic", "AWS EC2", "OCI", "Scaleway", "Hetzner"]
		root_public_key: DF.Code | None
		ssh_port: DF.Data | None
		ssh_user: DF.Data | None
		status: DF.Literal["Active", "Archived"]
		title: DF.Data
		virtual_machine: DF.Link | None
	# end: auto-generated types

	pass
