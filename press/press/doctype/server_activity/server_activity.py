# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from typing import Literal

import frappe
from frappe.model.document import Document


class ServerActivity(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Literal[
			"Created",
			"Reboot",
			"Volume",
			"Disk Size Change",
			"Terminated",
			"Incident",
		]
		document_name: DF.DynamicLink
		document_type: DF.Link
		reason: DF.SmallText | None
		team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ("action", "reason", "document_name")


def log_server_activity(
	series: Literal["f", "m"],
	server: str,
	action: Literal["Created", "Reboot", "Volume", "Terminated", "Disk Size Change"],
	reason: str | None = None,
) -> None:
	"""Create a log of server activity"""
	if series not in ["f", "m"]:
		return

	document_type = "Server" if series == "f" else "Database Server"
	team = frappe.db.get_value(document_type, server, "team")

	frappe.get_doc(
		{
			"doctype": "Server Activity",
			"document_type": document_type,
			"document_name": server,
			"action": action,
			"reason": reason,
			"team": team,
		}
	).insert()
