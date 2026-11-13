# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WazuhSCAPolicyResult(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		failed: DF.Int
		invalid: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		passed: DF.Int
		policy_id: DF.Data | None
		policy_name: DF.Data | None
		scan_end: DF.Datetime | None
		score: DF.Int
		total_checks: DF.Int
	# end: auto-generated types

	pass
