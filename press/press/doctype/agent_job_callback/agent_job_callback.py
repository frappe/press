# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AgentJobCallback(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_job: DF.Link
		job_name: DF.Data
		status: DF.Literal["Success", "Failure"]
	# end: auto-generated types

	pass
