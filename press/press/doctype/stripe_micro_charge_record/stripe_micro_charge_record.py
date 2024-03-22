# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document
from press.utils.billing import get_stripe


class StripeMicroChargeRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		has_been_refunded: DF.Check
		stripe_payment_intent_id: DF.Data
		stripe_payment_method: DF.Link | None
		team: DF.Link | None
	# end: auto-generated types

	def after_insert(self):
		# Auto-refund
		self.refund()

	@frappe.whitelist()
	def refund(self):
		stripe = get_stripe()
		refund = stripe.Refund.create(payment_intent=self.stripe_payment_intent_id)

		if refund.status == "succeeded":
			self.has_been_refunded = True
			self.save()
