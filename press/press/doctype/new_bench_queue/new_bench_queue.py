# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import typing

from frappe.model.document import Document


class NewBenchQueue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link | None
		group: DF.Link
		payload: DF.JSON
		status: DF.Literal["Queued", "Started", "Failure"]
	# end: auto-generated types

	dashboard_fields: typing.ClassVar = ["status", "group"]
