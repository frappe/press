# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from press.telegram_utils import Telegram


class PaymentDispute(Document):
	def after_insert(self):
		if self.event_type == "Created":
			telegram = Telegram(topic="Dispute", group="Billing")
			telegram.send(
				f"""
				⚠️  New dispute has been raised!

				Email: {self.email}
				Dispute ID: `{self.dispute_id}`
				[Payment reference on Stripe Dashboard](https://dashboard.stripe.com/payments/{self.payment_intent})
			"""
			)
