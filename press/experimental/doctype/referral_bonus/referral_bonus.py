# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document


class ReferralBonus(Document):
	@frappe.whitelist()
	def allocate_credits(self):
		# Credits have already been allocated
		if self.credits_allocated:
			return

		# Team hasn't spent any money yet
		if not self.team_has_spent():
			return

		team = frappe.get_doc("Team", self.referred_by)
		credits_field = "free_credits_inr" if team.currency == "INR" else "free_credits_usd"
		credit_amount = frappe.db.get_single_value("Press Settings", credits_field)
		if not credit_amount:
			return

		team.allocate_credit_amount(credit_amount, source="Referral Bonus")

		self.credits_allocated = True
		self.save()
		self.reload()

	def team_has_spent(self):
		"""Has the `for_team` spent any money yet (stripe)"""
		return (
			frappe.db.count(
				"Invoice",
				filters={"team": self.for_team, "status": "Paid", "transaction_amount": (">", 0)},
			)
			> 0
		)
