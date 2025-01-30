# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class SSHAccessAuditViolation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		host: DF.Data | None
		key: DF.Code | None
		key_doctype: DF.Link | None
		key_document: DF.DynamicLink | None
		key_field: DF.Data | None
		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		user: DF.Data | None
	# end: auto-generated types

	pass
