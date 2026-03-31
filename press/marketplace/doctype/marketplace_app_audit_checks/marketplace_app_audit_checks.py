# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MarketplaceAppAuditChecks(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Literal[
			"",
			"Metadata",
			"Versioning",
			"Dependencies",
			"Code Quality",
			"Security",
			"Compatibility",
			"Operational",
		]
		check_id: DF.Data
		check_name: DF.Data
		details: DF.Code | None
		message: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		remediation: DF.SmallText | None
		result: DF.Literal["Pass", "Warn", "Fail", "Skipped", "Error"]
		severity: DF.Literal["", "Critical", "Major", "Minor", "Info"]
	# end: auto-generated types

	pass
