# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class SiteMigrationStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		method_arg: DF.Data | None
		method_name: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal[
			"Pending", "Running", "Success", "Failure", "Skipped", "Delivery Failure"
		]
		step_job: DF.Link | None
		step_title: DF.Data
	# end: auto-generated types

	pass
