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

		from press.press.doctype.cloud_cost_account.cloud_cost_account import CloudCostAccount

		accounts: DF.Table[CloudCostAccount]
		backfill_months: DF.Int
		baseline_days: DF.Int
		enabled: DF.Check
		level_shift_minimum_change: DF.Percent
		minimum_daily_cost_impact: DF.Currency
		minimum_series_cost: DF.Currency
		organic_tolerance: DF.Percent
		restatement_days: DF.Int
		retention_days: DF.Int
		spike_mad_threshold: DF.Float
	# end: auto-generated types

	def validate(self):
		self.validate_unique_labels()

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
		from press.press.doctype.cloud_usage_driver.cloud_usage_driver import (
			backfill_upload_drivers,
		)

		backfill_upload_drivers(self.backfill_months or 14)

	def validate_unique_labels(self):
		"""Every account's rows are stored under its label, so two accounts sharing one
		label would silently merge into a single series."""
		labels = [row.label for row in self.accounts]
		duplicates = {label for label in labels if labels.count(label) > 1}
		if duplicates:
			frappe.throw(f"Account labels must be unique. Repeated: {', '.join(sorted(duplicates))}")
