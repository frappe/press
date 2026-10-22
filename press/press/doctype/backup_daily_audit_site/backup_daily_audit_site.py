# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.model.document import Document


class BackupDailyAuditSite(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		failed_backups: DF.Int
		last_successful_backup: DF.Datetime | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		plan: DF.Link | None
		server: DF.Link | None
		site: DF.Link
		team: DF.Link | None
	# end: auto-generated types

	pass
