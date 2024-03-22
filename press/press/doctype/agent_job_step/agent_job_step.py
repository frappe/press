# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AgentJobStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_job: DF.Link
		data: DF.Code | None
		duration: DF.Time | None
		end: DF.Datetime | None
		output: DF.Code | None
		start: DF.Datetime | None
		status: DF.Literal[
			"Pending", "Running", "Success", "Failure", "Skipped", "Delivery Failure"
		]
		step_name: DF.Data
		traceback: DF.Code | None
	# end: auto-generated types

	pass
