# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document
from press.utils.billing import get_stripe


class StripeMicroChargeRecord(Document):
	@frappe.whitelist()
	def refund(self):
		stripe = get_stripe()
		refund = stripe.Refund.create(payment_intent=self.stripe_payment_intent_id)

		if refund.status == "succeeded":
			self.has_been_refunded = True
			self.save()
