# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import re

import frappe
from frappe.utils import flt, fmt_money
from press.utils import get_current_team
from press.utils.billing import (
	clear_setup_intent,
	get_erpnext_com_connection,
	get_publishable_key,
	get_setup_intent,
	get_stripe,
	make_formatted_doc,
	states_with_tin,
)


@frappe.whitelist()
def get_publishable_key_and_setup_intent():
	team = get_current_team()
	return {
		"publishable_key": get_publishable_key(),
		"setup_intent": get_setup_intent(team),
	}


@frappe.whitelist()
def info():
	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)
	invoice = team_doc.get_upcoming_invoice()
	currency = team_doc.currency

	if invoice:
		upcoming_invoice = invoice.as_dict()
		upcoming_invoice.formatted_total = invoice.get_formatted("total")
	else:
		upcoming_invoice = None

	past_invoices = team_doc.get_past_invoices()

	if team_doc.billing_address:
		address = frappe.get_doc("Address", team_doc.billing_address)
		address_parts = [
			address.address_line1,
			address.city,
			address.state,
			address.country,
			address.pincode,
		]
		billing_address = ", ".join([d for d in address_parts if d])
	else:
		billing_address = ""

	return {
		"upcoming_invoice": upcoming_invoice,
		"past_invoices": past_invoices,
		"billing_address": billing_address,
		"payment_method": team_doc.default_payment_method,
		"available_credits": fmt_money(team_doc.get_balance(), 2, currency),
	}


@frappe.whitelist()
def get_customer_details(team):
	"""This method is called by frappe.io for creating Customer and Address"""
	team_doc = frappe.db.get_value("Team", team, "*")
	return {
		"team": team_doc,
		"address": frappe.get_doc("Address", team_doc.billing_address),
	}


@frappe.whitelist()
def transfer_partner_credits(amount):
	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)
	partner_email = team_doc.user
	erpnext_com = get_erpnext_com_connection()

	res = erpnext_com.post_api(
		"central.api.consume_partner_credits",
		{"email": partner_email, "currency": team_doc.currency, "amount": amount},
	)

	if res.get("error_message"):
		frappe.throw(res.get("error_message"))

	transferred_credits = flt(res["transferred_credits"])
	transaction_id = res["transaction_id"]

	team_doc.allocate_credit_amount(
		transferred_credits,
		source="Transferred Credits",
		remark="Transferred Credits from ERPNext Cloud. Transaction ID: {0}".format(
			transaction_id
		),
	)

	if (team_doc.currency == "INR" and amount == 1000) or (
		team_doc.currency == "USD" and amount == 10
	):
		# via onboarding
		team_doc.update_onboarding("Transfer Credits", "Completed")


@frappe.whitelist()
def get_available_partner_credits():
	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)
	partner_email = team_doc.user
	erpnext_com = get_erpnext_com_connection()

	available_credits = erpnext_com.post_api(
		"central.api.get_available_partner_credits", {"email": partner_email},
	)
	return {
		"value": available_credits,
		"formatted": fmt_money(available_credits, 2, team_doc.currency),
	}


@frappe.whitelist()
def create_payment_intent_for_buying_credits(amount):
	team = get_current_team(True)
	stripe = get_stripe()
	intent = stripe.PaymentIntent.create(
		amount=amount * 100,
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Prepaid Credits",
	)
	return {
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


@frappe.whitelist()
def get_payment_methods():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_payment_methods()


@frappe.whitelist()
def get_invoice_usage(invoice):
	team = get_current_team()
	# apply team filter for safety
	doc = frappe.get_doc("Invoice", {"name": invoice, "team": team})
	out = doc.as_dict()
	# a dict with formatted currency values for display
	out.formatted = make_formatted_doc(doc)
	out.invoice_pdf = doc.invoice_pdf or (doc.currency == "USD" and doc.get_pdf())
	return out


@frappe.whitelist()
def after_card_add():
	clear_setup_intent()


@frappe.whitelist()
def setup_intent_success(setup_intent, address):
	setup_intent = frappe._dict(setup_intent)
	address = frappe._dict(address)

	team = get_current_team(True)
	clear_setup_intent()
	team.create_payment_method(setup_intent.payment_method, set_default=True)
	team.update_billing_details(address)
	team.update_onboarding("Add Billing Information", "Completed")


@frappe.whitelist()
def indian_states():
	return states_with_tin.keys()


@frappe.whitelist()
def validate_gst(address, method=None):
	if isinstance(address, dict):
		address = frappe._dict(address)

	if address.country != "India":
		return

	if address.state not in states_with_tin:
		frappe.throw("Invalid State for India.")

	if not address.gstin:
		frappe.throw("GSTIN is required for Indian customers.")

	if address.gstin and address.gstin != "Not Applicable":
		pattern = re.compile(
			"^[0-9]{2}[A-Z]{4}[0-9A-Z]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[1-9A-Z]{1}[0-9A-Z]{1}$"
		)
		if not pattern.match(address.gstin):
			frappe.throw(
				"Invalid GSTIN. The input you've entered does not match the format of GSTIN."
			)

		tin_code = states_with_tin[address.state]
		if not address.gstin.startswith(tin_code):
			frappe.throw(f"GSTIN must start with {tin_code} for {address.state}.")
