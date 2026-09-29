# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

from frappe.model.document import Document

if TYPE_CHECKING:
	from datetime import datetime

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class ScheduledDeployGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		friday: DF.Check
		hour: DF.Int
		monday: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		release_group: DF.Link
		saturday: DF.Check
		sunday: DF.Check
		thursday: DF.Check
		tuesday: DF.Check
		wednesday: DF.Check
	# end: auto-generated types

	def is_due(self, now: datetime) -> bool:
		return self.hour == now.hour and bool(self.get(WEEKDAYS[now.weekday()]))
