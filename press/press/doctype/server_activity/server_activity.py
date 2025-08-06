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

		action: DF.Literal["Created", "Reboot", "Volume", "Disk Size Change", "Terminated"]
		document_name: DF.DynamicLink
		document_type: DF.Link
		reason: DF.SmallText | None
		team: DF.Link | None
	# end: auto-generated types

<<<<<<< HEAD
<<<<<<< HEAD
	dashboard_fields = ("action", "reason", "document_name")
=======
	dashboard_fields = ("action", "reason", "site", "job")
>>>>>>> a9dde025a (feat(server-log): Add logs for basic server events)
=======
	dashboard_fields = ("action", "reason", "document_name")
>>>>>>> 162d53a52 (feat(server-log): Add initial logs)


def log_server_activity(
	series: Literal["f", "m"],
	server: str,
	action: Literal["Created", "Reboot", "Volume", "Terminated", "Disk Size Change"],
<<<<<<< HEAD
<<<<<<< HEAD
	reason: str | None = None,
=======
	reason: str,
	team: str,
>>>>>>> a9dde025a (feat(server-log): Add logs for basic server events)
=======
	reason: str | None = None,
	team: str | None = None,
>>>>>>> 162d53a52 (feat(server-log): Add initial logs)
) -> None:
	"""Create a log of server activity"""
	if series not in ["f", "m"]:
		return

<<<<<<< HEAD
	document_type = "Server" if series == "f" else "Database Server"
	team = frappe.db.get_value(document_type, server, "team")

	frappe.get_doc(
		{
			"doctype": "Server Activity",
			"document_type": document_type,
			"document_name": server,
=======
	frappe.get_doc(
		{
			"doctype": "Server Activity",
<<<<<<< HEAD
			"document_name": "Server" if series == "f" else "Database Server",
			"document_type": server,
>>>>>>> a9dde025a (feat(server-log): Add logs for basic server events)
=======
			"document_type": "Server" if series == "f" else "Database Server",
			"document_name": server,
>>>>>>> 162d53a52 (feat(server-log): Add initial logs)
			"action": action,
			"reason": reason,
			"team": team,
		}
	).insert()
