# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.model.document import Document


class WAFBlockedParameter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		endpoint: DF.Data | None
		location: DF.Literal["ARGS", "REQUEST_BODY", "REQUEST_HEADERS", "REQUEST_COOKIES"]
		match_type: DF.Literal["", "Exists", "Equals", "Contains", "Regex"]
		parameter: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		value: DF.Data | None
	# end: auto-generated types

	pass
