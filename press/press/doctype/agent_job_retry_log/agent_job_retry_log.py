# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days


class AgentJobRetryLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_job: DF.Link | None
		retried_at: DF.Datetime | None
		retry_log: DF.Code | None
		server: DF.DynamicLink | None
		server_type: DF.Literal["Database Server", "Server", "Proxy Server"]
	# end: auto-generated types

	pass


def remove_stale_logs():
	frappe.db.delete(
		"Agent Job Retry Log", {"creation": ("<=", add_days(nowdate(), days=-3))}
	)
