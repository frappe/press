# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceAppPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link | None
		commission_inr: DF.Currency
		commission_usd: DF.Currency
		team: DF.Link | None
		total_inr: DF.Currency
		total_usd: DF.Currency
	# end: auto-generated types

	def get_commission(self, row_amount, currency):
		"""
		Calculate commission based on threshold logic:
		- Below threshold: Commission = min(row_amount, remaining_to_reach_threshold)
		- At/above threshold: Commission = row_amount * commission_rate
		"""
		press_settings = frappe.get_cached_doc("Press Settings")
		exchange_rate = press_settings.usd_rate or 80
		threshold = press_settings.threshold
		commission_rate = press_settings.commission

		# Calculate current total in USD
		current_total = self.total_usd + (self.total_inr / exchange_rate)

		if current_total >= threshold:
			# Already above threshold, apply commission rate to entire amount
			return row_amount * commission_rate

		# Below threshold -> check if this transaction crosses it
		new_total = current_total + (row_amount / exchange_rate if currency == "INR" else row_amount)

		if new_total <= threshold:
			# Still below threshold, full amount as commission
			return row_amount

		# Transaction crosses threshold -> partial commission
		amount_to_threshold = threshold - current_total

		if currency == "INR":
			amount_to_threshold = amount_to_threshold * exchange_rate

		amount_above_threshold = row_amount - amount_to_threshold
		return amount_to_threshold + (amount_above_threshold * commission_rate)
