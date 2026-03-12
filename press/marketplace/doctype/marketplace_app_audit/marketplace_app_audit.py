# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class MarketplaceAppAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.marketplace.doctype.marketplace_app_audit_checks.marketplace_app_audit_checks import (
			MarketplaceAppAuditChecks,
		)

		app_release: DF.Link
		approval_request: DF.Link | None
		audit_checks: DF.Table[MarketplaceAppAuditChecks]
		audit_summary: DF.LongText | None
		audit_type: DF.Literal["", "Submission Gate", "Manual Run", "Scheduled Audit"]
		finished_at: DF.Datetime | None
		marketplace_app: DF.Link
		result: DF.Literal["Pass", "Warn", "Fail"]
		started_at: DF.Datetime | None
		status: DF.Literal["Queued", "Running", "Completed", "Failed"]
		team: DF.Link | None
	# end: auto-generated types

	def autoname(self):
		# AUD-{marketplace_app}-.#####
		series = f"AUD-{self.marketplace_app}-.#####"
		self.name = make_autoname(series)
