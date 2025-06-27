# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.model.document import Document


class AgentUpdateServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_status: DF.Literal["", "Inactive", "Active"]
		current_commit: DF.Data | None
		end: DF.Datetime | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reason_of_fatal_status: DF.Data | None
		rollback_ansible_play: DF.Link | None
		rollback_commit: DF.Data | None
		server: DF.DynamicLink
		server_type: DF.Literal["Server", "Database Server", "Proxy Server"]
		start: DF.Datetime | None
		status: DF.Literal[
			"Draft",
			"Pending",
			"Running",
			"Success",
			"Failure",
			"Fatal",
			"Skipped",
			"Rolling Back",
			"Rolled Back",
		]
		status_check_started_on: DF.Datetime | None
		update_ansible_play: DF.Link | None
	# end: auto-generated types
