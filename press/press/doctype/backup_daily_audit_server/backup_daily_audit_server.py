# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.model.document import Document


class BackupDailyAuditServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cloud_provider: DF.Data | None
		failed_snapshots: DF.Int
		last_successful_snapshot: DF.Datetime | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		series: DF.Data | None
		server: DF.DynamicLink | None
		server_type: DF.Link | None
		team: DF.Link | None
		virtual_machine: DF.Link
	# end: auto-generated types

	pass
