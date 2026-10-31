# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CloudCostSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		backfill_months: DF.Int
		do_snapshot_rate: DF.Currency
		do_volume_rate: DF.Currency
		enabled: DF.Check
		minimum_daily_cost_impact: DF.Currency
		minimum_series_cost: DF.Currency
		restatement_days: DF.Int
		retention_days: DF.Int
	# end: auto-generated types

	@frappe.whitelist()
	def backfill_cost_history(self):
		"""Cost Explorer holds fourteen months of daily data and charges a cent a
		request, so this is a deliberate button rather than something the scheduler
		decides to do."""
		frappe.only_for("System Manager")
		frappe.enqueue_doc(self.doctype, self.name, "_backfill_cost_history", queue="long", timeout=3600)
		return f"Queued. Loading {self.backfill_months or 14} months of daily cost."

	def _backfill_cost_history(self):
		from press.press.doctype.cloud_cost_daily.cloud_cost_daily import backfill_history

		backfill_history()

	@frappe.whitelist()
	def backfill_driver_history(self):
		"""Remote File rows are never deleted, so the upload series can be rebuilt for
		the whole history rather than starting from today like the other drivers."""
		frappe.only_for("System Manager")
		frappe.enqueue_doc(self.doctype, self.name, "_backfill_driver_history", queue="long", timeout=3600)
		return "Queued. Rebuilding the backup upload series from Remote File."

	def _backfill_driver_history(self):
		from press.press.doctype.cloud_usage_driver.cloud_usage_driver import backfill_upload_drivers

		backfill_upload_drivers(self.backfill_months or 14)
