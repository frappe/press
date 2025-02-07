# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any

from frappe.model.document import Document


class SQLJobQuery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		columns: DF.JSON | None
		data: DF.JSON | None
		duration: DF.Duration | None
		error_code: DF.Data | None
		error_message: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		profile: DF.JSON | None
		query: DF.SmallText
		row_count: DF.Int
		skip: DF.Check
		success: DF.Check
	# end: auto-generated types

	@property
	def columns_list(self) -> list[str]:
		try:
			return json.loads(self.columns)
		except Exception:
			return []

	@property
	def profile_dict(self) -> dict[str, Any]:
		try:
			return json.loads(self.profile)
		except Exception:
			return {}

	@property
	def result_list(self) -> list[list[Any]]:
		try:
			return json.loads(self.result)
		except Exception:
			return []

	def is_ddl_query(self) -> bool:
		return self.query.upper().startswith(("CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME", "COMMENT"))

	def is_restricted_query(self) -> bool:
		return self.query.upper().startswith(
			("GRANT", "REVOKE", "SHOW", "USE", "COMMIT", "ROLLBACK", "KILL", "BEGIN", "END", "SET", "LOCK")
		)

	def is_select_query(self) -> bool:
		if len(self.query) < 6:
			return False
		return self.query[:6] in ("SELECT", "select")
