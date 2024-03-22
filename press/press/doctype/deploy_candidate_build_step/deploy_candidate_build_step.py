# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class DeployCandidateBuildStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cached: DF.Check
		command: DF.Code | None
		duration: DF.Float
		hash: DF.Data | None
		lines: DF.Code | None
		output: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		stage: DF.Data
		stage_slug: DF.Data
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		step: DF.Data
		step_index: DF.Int
		step_slug: DF.Data
	# end: auto-generated types

	pass
