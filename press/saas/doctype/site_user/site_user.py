# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from frappe.model.document import Document


class SiteUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		site: DF.Link
		user: DF.Data
		# end: auto-generated types

		pass
