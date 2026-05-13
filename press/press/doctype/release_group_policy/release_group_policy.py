# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ReleaseGroupPolicy(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.release_group_policy_app.release_group_policy_app import (
			ReleaseGroupPolicyApp,
		)

		policies: DF.Table[ReleaseGroupPolicyApp]
		policy_name: DF.Data
		scope: DF.Link
		status: DF.Literal["Active", "Disabled"]
		target: DF.DynamicLink | None
	# end: auto-generated types
	pass
