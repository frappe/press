# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BenchSiteUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		server: DF.Link | None
		site: DF.Link
		site_update: DF.Link | None
		skip_backups: DF.Check
		skip_failing_patches: DF.Check
		source_candidate: DF.Link | None
		status: DF.Literal["Pending", "Running", "Failure", "Recovered", "Success", "Fatal"]
	# end: auto-generated types

	pass
