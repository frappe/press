# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from frappe.model.document import Document

from press.overrides import get_permission_query_conditions_for_doctype


class SQLPlaygroundLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		committed: DF.Check
		query: DF.SmallText | None
		site: DF.Link | None
		team: DF.Link | None
	# end: auto-generated types

	DOCTYPE = "SQL Playground Log"
	dashboard_fields = (
		"site",
		"query",
		"committed",
	)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("SQL Playground Log")
