# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from press.telegram_utils import Telegram


class PaymentDispute(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dispute_id: DF.Data | None
		email: DF.Data | None
		event_type: DF.Data | None
		payment_intent: DF.Data | None
	# end: auto-generated types

	def after_insert(self):
		telegram = Telegram(topic="Disputes", group="Billing")
		telegram.send(
			f"""
			Dispute Update!

			Email: {self.email}
			Dispute ID: `{self.dispute_id}`
			Event: `{self.event_type}`
			[Payment reference on Stripe Dashboard](https://dashboard.stripe.com/payments/{self.payment_intent})
		"""
		)
