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
		if not team_has_spent(self.for_team):
			self.add_comment(
				text="Cannot credit referral bonus. The team hasn't spent any money yet."
			)
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


def team_has_spent(team):
	"""Has the `for_team` spent any money yet (stripe)"""
	return (
		frappe.db.count(
			"Invoice", filters={"team": team, "status": "Paid", "transaction_amount": (">", 0)},
		)
		> 0
	)


def credit_referral_bonuses():
	unallocated_referral_bonuses = frappe.get_all(
		"Referral Bonus",
		filters={"credits_allocated": False},
		fields=["name", "for_team", "referred_by"],
	)

	for rb in unallocated_referral_bonuses:
		if team_has_spent(rb.for_team):
			try:
				frappe.get_doc("Referral Bonus", rb.name).allocate_credits()
			except Exception:
				pass
