# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MariaDBAnalyzeQuery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.mariadb_analyze_query_tables.mariadb_analyze_query_tables import (
			MariaDBAnalyzeQueryTables,
		)

		explain_output: DF.Code | None
		query: DF.Data
		site: DF.Data
		status: DF.Data | None
		suggested_index: DF.Data | None
		tables_in_query: DF.Table[MariaDBAnalyzeQueryTables]
	# end: auto-generated types

	pass
