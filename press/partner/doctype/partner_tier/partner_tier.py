# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PartnerTier(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		target_in_inr: DF.Float
		target_in_usd: DF.Float
		title: DF.Data | None
	# end: auto-generated types

	pass
