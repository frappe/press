# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IPRemovalLogSteps(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_ping: DF.Literal["Pending", "Success", "Failure"]
		attempt: DF.Int
		job: DF.DynamicLink | None
		job_type: DF.Link | None
		method_name: DF.Data | None
		output: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		server: DF.Data | None
		server_ping: DF.Literal["Pending", "Success", "Failure"]
		status: DF.Literal["Pending", "Running", "Success", "Skipped", "Failure"]
	# end: auto-generated types

	pass
