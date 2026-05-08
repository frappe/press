# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AgentAuth(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		expires_in: DF.Datetime | None
		is_agent_auth_setup: DF.Check
		public_key: DF.Data | None
		regenerate_public_key: DF.Data | None
		server: DF.Data | None
		server_type: DF.Data | None
	# end: auto-generated types

	pass
