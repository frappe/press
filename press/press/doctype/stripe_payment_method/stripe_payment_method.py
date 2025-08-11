# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document

from press.api.billing import get_stripe
from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error
from press.utils.telemetry import capture


class StripePaymentMethod(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		brand: DF.Data | None
		expiry_month: DF.Data | None
		expiry_year: DF.Data | None
		is_default: DF.Check
		is_verified_with_micro_charge: DF.Check
		last_4: DF.Data | None
		name_on_card: DF.Data | None
		stripe_customer_id: DF.Data | None
		stripe_mandate_id: DF.Data | None
		stripe_mandate_reference: DF.Data | None
		stripe_payment_method_id: DF.Data | None
		stripe_setup_intent_id: DF.Data | None
		team: DF.Link
	# end: auto-generated types

	dashboard_fields = (
		"is_default",
		"expiry_month",
		"expiry_year",
		"brand",
		"name_on_card",
		"last_4",
		"stripe_mandate_id",
	)

	def onload(self):
		load_address_and_contact(self)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		StripeWebhookLog = frappe.qb.DocType("Stripe Webhook Log")
		StripePaymentMethod = frappe.qb.DocType("Stripe Payment Method")

		query = (
			query.select(StripeWebhookLog.stripe_payment_method)
			.left_join(StripeWebhookLog)
			.on(
				(StripeWebhookLog.stripe_payment_method == StripePaymentMethod.name)
				& (StripeWebhookLog.event_type == "payment_intent.payment_failed")
			)
			.distinct()
		)

		return query  # noqa: RET504

	@dashboard_whitelist()
	def delete(self):
		if webhook_logs := frappe.get_all(
			"Stripe Webhook Log",
			filters={"stripe_payment_method": self.name},
			pluck="name",
		):
			frappe.db.set_value(
				"Stripe Webhook Log",
				{"name": ("in", webhook_logs)},
				"stripe_payment_method",
				None,
			)

		super().delete()

	@dashboard_whitelist()
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
			account_request_name = frappe.get_value("Team", self.team, "account_request")
			if account_request_name:
				account_request = frappe.get_doc("Account Request", account_request_name)
				if not (account_request.is_saas_signup() or account_request.invited_by_parent_team):
					capture("added_card_or_prepaid_credits", "fc_signup", account_request.email)

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

	@frappe.whitelist()
	def check_mandate_status(self):
		if not self.stripe_mandate_id:
			return False

		stripe = get_stripe()
		mandate = stripe.Mandate.retrieve(self.stripe_mandate_id)
		return mandate.status


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Stripe Payment Method")


def on_doctype_update():
	frappe.db.add_index("Stripe Payment Method", ["team", "is_verified_with_micro_charge"])
