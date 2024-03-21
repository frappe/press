# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ScheduledAutoUpdateLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		error: DF.Text | None
		status: DF.Literal["Failed", "Success"]
		was_scheduled_for_day: DF.Data | None
		was_scheduled_for_frequency: DF.Data | None
		was_scheduled_for_month_day: DF.Data | None
		was_scheduled_for_month_end: DF.Check
		was_scheduled_for_time: DF.Time | None
	# end: auto-generated types

	pass
