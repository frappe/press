# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.api.billing import get_stripe
from frappe.contacts.address_and_contact import load_address_and_contact


class StripePaymentMethod(Document):
	def onload(self):
		load_address_and_contact(self)

	def after_insert(self):
		country = frappe.db.get_value("Country", {"code": self.address_country.lower()})
		address = frappe.get_doc(
			doctype="Address",
			address_title=self.team,
			address_line1=self.address_line1,
			city=self.address_city,
			state=self.address_state,
			pincode=self.address_postal_code,
			country=country,
			links=[
				{"link_doctype": self.doctype, "link_name": self.name, "link_title": self.team},
				{"link_doctype": "Team", "link_name": self.team, "link_title": self.team},
			],
		)
		address.insert()

	def set_default(self):
		stripe = get_stripe()
		# set default payment method on stripe
		stripe.Customer.modify(
			self.stripe_customer_id,
			invoice_settings={"default_payment_method": self.stripe_payment_method_id},
		)
		frappe.db.update(
			"Stripe Payment Method",
			{"team": self.team, "name": ("!=", self.name)},
			"is_default",
			0,
		)
		self.is_default = 1
		self.save()
		frappe.db.set_value("Team", self.team, "default_payment_method", self.name)
