# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

import frappe

from frappe.utils import fmt_money
from press.utils import get_current_team
from press.utils.billing import (
	clear_setup_intent,
	get_publishable_key,
	get_setup_intent,
	get_stripe,
	make_formatted_doc,
	states_with_tin,
	validate_gstin_check_digit,
	GSTIN_FORMAT,
)


@frappe.whitelist()
def get_publishable_key_and_setup_intent():
	team = get_current_team()
	return {
		"publishable_key": get_publishable_key(),
		"setup_intent": get_setup_intent(team),
	}


@frappe.whitelist()
def upcoming_invoice():
	team = get_current_team(True)
	invoice = team.get_upcoming_invoice()

	if invoice:
		upcoming_invoice = invoice.as_dict()
		upcoming_invoice.formatted = make_formatted_doc(invoice, ["Currency"])
	else:
		upcoming_invoice = None

	return {
		"upcoming_invoice": upcoming_invoice,
		"available_credits": fmt_money(team.get_balance(), 2, team.currency),
	}


@frappe.whitelist()
def past_invoices():
	return get_current_team(True).get_past_invoices()


@frappe.whitelist()
def invoices_and_payments():
	team = get_current_team(True)
	invoices = team.get_past_invoices()
	return invoices


@frappe.whitelist()
def balances():
	team = get_current_team()
	has_bought_credits = frappe.db.get_all(
		"Balance Transaction",
		filters={
			"source": ("in", ("Prepaid Credits", "Transferred Credits")),
			"team": team,
			"docstatus": 1,
		},
		limit=1,
	)
	if not has_bought_credits:
		return []

	data = frappe.db.get_all(
		"Balance Transaction",
		filters={"team": team, "docstatus": 1},
		fields=["*"],
		order_by="creation desc",
	)
	for d in data:
		d.formatted = dict(
			amount=fmt_money(d.amount, 2, d.currency),
			ending_balance=fmt_money(d.ending_balance, 2, d.currency),
		)
	return data


@frappe.whitelist()
def details():
	team = get_current_team(True)
	address = None
	if team.billing_address:
		address = frappe.get_doc("Address", team.billing_address)
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
		"billing_name": team.billing_name,
		"billing_address": billing_address,
		"gstin": address.gstin if address else None,
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
def set_as_default(name):
	payment_method = frappe.get_doc(
		"Stripe Payment Method", {"name": name, "team": get_current_team()}
	)
	payment_method.set_default()


@frappe.whitelist()
def remove_payment_method(name):
	payment_method = frappe.get_doc(
		"Stripe Payment Method", {"name": name, "team": get_current_team()}
	)
	payment_method.delete()


@frappe.whitelist()
def change_payment_mode(mode):
	team = get_current_team(get_doc=True)
	team.payment_mode = mode
	team.save()


@frappe.whitelist()
def prepaid_credits_via_onboarding():
	"""When prepaid credits are bought, the balance is not immediately reflected.
	This method will check balance every second and then set payment_mode"""
	from time import sleep

	team = get_current_team(get_doc=True)

	seconds = 0
	# block until balance is updated
	while team.get_balance() == 0 or seconds > 20:
		seconds += 1
		sleep(1)
		frappe.db.rollback()

	team.payment_mode = "Prepaid Credits"
	team.save()


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
def setup_intent_success(setup_intent, address=None):
	setup_intent = frappe._dict(setup_intent)
	team = get_current_team(True)
	clear_setup_intent()
	team.create_payment_method(setup_intent.payment_method, set_default=True)
	if address:
		address = frappe._dict(address)
		team.update_billing_details(address)


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
		if not GSTIN_FORMAT.match(address.gstin):
			frappe.throw(
				"Invalid GSTIN. The input you've entered does not match the format of GSTIN."
			)

		tin_code = states_with_tin[address.state]
		if not address.gstin.startswith(tin_code):
			frappe.throw(f"GSTIN must start with {tin_code} for {address.state}.")

		validate_gstin_check_digit(address.gstin)


@frappe.whitelist()
def get_latest_unpaid_invoice():
	team = get_current_team()
	unpaid_invoices = frappe.get_all(
		"Invoice",
		{"team": team, "status": "Unpaid", "payment_attempt_count": (">", 0)},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)

	if unpaid_invoices:
		unpaid_invoice = frappe.db.get_value(
			"Invoice",
			unpaid_invoices[0],
			["amount_due", "stripe_invoice_url", "payment_mode", "amount_due", "currency"],
			as_dict=True,
		)
		if (
			unpaid_invoice.payment_mode == "Prepaid Credits"
			and team_has_balance_for_invoice(unpaid_invoice)
		):
			return

		return unpaid_invoice


def team_has_balance_for_invoice(prepaid_mode_invoice):
	team = get_current_team(get_doc=True)
	return team.get_balance() >= prepaid_mode_invoice.amount_due


@frappe.whitelist()
def get_partner_credits():
	team = get_current_team(get_doc=True)
	available_credits = team.get_available_partner_credits()
	return fmt_money(available_credits, 2, team.currency)
