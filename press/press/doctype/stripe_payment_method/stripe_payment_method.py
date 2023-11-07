# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.api.billing import get_stripe
from frappe.contacts.address_and_contact import load_address_and_contact
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error


class StripePaymentMethod(Document):
	def onload(self):
		load_address_and_contact(self)

	def set_default(self):
		stripe = get_stripe()
		# set default payment method on stripe
		stripe.Customer.modify(
			self.stripe_customer_id,
			invoice_settings={"default_payment_method": self.stripe_payment_method_id},
		)
		frappe.db.set_value(
			"Stripe Payment Method",
			{"team": self.team, "name": ("!=", self.name)},
			"is_default",
			0,
		)
		self.is_default = 1
		self.save()
		frappe.db.set_value("Team", self.team, "default_payment_method", self.name)
		if not frappe.db.get_value("Team", self.team, "payment_mode"):
			frappe.db.set_value("Team", self.team, "payment_mode", "Card")

	def on_trash(self):
		self.remove_address_links()
		self.remove_micro_charge_links()

		if self.is_default:
			team = frappe.get_doc("Team", self.team)
			team.default_payment_method = None
			team.save()

	def remove_address_links(self):
		address_links = frappe.db.get_all(
			"Dynamic Link",
			{"link_doctype": "Stripe Payment Method", "link_name": self.name},
			pluck="parent",
		)
		address_links = list(set(address_links))
		for address in address_links:
			found = False
			doc = frappe.get_doc("Address", address)
			for link in doc.links:
				print(link)
				if link.link_doctype == "Stripe Payment Method" and link.link_name == self.name:
					found = True
					doc.remove(link)
			if found:
				print(doc)
				doc.save()

	def remove_micro_charge_links(self):
		frappe.db.set_value(
			"Stripe Micro Charge Record",
			{"stripe_payment_method": self.name},
			"stripe_payment_method",
			None,
		)

	def after_delete(self):
		try:
			stripe = get_stripe()
			stripe.PaymentMethod.detach(self.stripe_payment_method_id)
		except Exception as e:
			log_error("Failed to detach payment method from stripe", data=e)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Stripe Payment Method"
)
