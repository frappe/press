# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from press.press.doctype.server.server import BaseServer


class BastionServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cluster: DF.Link | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		hostname: DF.Data | None
		hostname_abbreviation: DF.Data | None
		ip: DF.Data | None
		is_default: DF.Check
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		ssh_port: DF.Data | None
		ssh_user: DF.Data | None
		status: DF.Literal["Active", "Archived"]
		title: DF.Data | None
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate_agent_password(self):
		# ignore validation as bastion host will not have agent on it
		pass
