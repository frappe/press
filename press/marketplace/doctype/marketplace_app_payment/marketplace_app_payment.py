# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceAppPayment(Document):
	def has_threshold_passed(self):
		total = self.total_usd + (
			self.total_inr / frappe.db.get_single_value("Press Settings", "usd_rate")
		)
		return total > frappe.db.get_single_value("Press Settings", "threshold")

	def get_commission(self, total):
		# TODO: Handle partial commission
		# if first month collection: $20, second month: $1000 and $500 - cap/threshold
		# then commission should be calculated for $520 from second month collection onwards
		return (
			total * frappe.db.get_single_value("Press Settings", "commission")
			if self.has_threshold_passed()
			else 0.0
		)
