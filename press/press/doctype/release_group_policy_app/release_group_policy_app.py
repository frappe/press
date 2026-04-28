# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ReleaseGroupPolicyApp(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_on_creation: DF.Check
		app: DF.Link
		for_updates: DF.Check
		install_on_site_creation: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		release: DF.Link | None
		source: DF.Link
	# end: auto-generated types
	pass
