# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

import frappe

from typing import Dict, List
from itertools import groupby
from frappe.utils import fmt_money
from frappe.core.utils import find
from press.utils import get_current_team
from press.utils.billing import (
	clear_setup_intent,
	get_publishable_key,
	get_setup_intent,
	get_razorpay_client,
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

	bt = frappe.qb.DocType("Balance Transaction")
	inv = frappe.qb.DocType("Invoice")
	query = (
		frappe.qb.from_(bt)
		.left_join(inv)
		.on(bt.invoice == inv.name)
		.select(
			bt.name,
			bt.creation,
			bt.amount,
			bt.currency,
			bt.source,
			bt.type,
			bt.ending_balance,
			bt.description,
			inv.period_start,
		)
		.where((bt.docstatus == 1) & (bt.team == team))
		.orderby(bt.creation, order=frappe.qb.desc)
	)

	data = query.run(as_dict=True)
	for d in data:
		d.formatted = dict(
			amount=fmt_money(d.amount, 2, d.currency),
			ending_balance=fmt_money(d.ending_balance, 2, d.currency),
		)

		if d.period_start:
			d.formatted["invoice_for"] = d.period_start.strftime("%B %Y")
	return data


def get_processed_balance_transactions(transactions: List[Dict]):
	"""Cleans up transactions and adjusts ending balances accordingly"""

	cleaned_up_transations = get_cleaned_up_transactions(transactions)
	processed_balance_transactions = []
	for bt in reversed(cleaned_up_transations):
		if is_added_credits_bt(bt) and len(processed_balance_transactions) < 1:
			processed_balance_transactions.append(bt)
		elif is_added_credits_bt(bt):
			bt.ending_balance += processed_balance_transactions[
				-1
			].ending_balance  # Adjust the ending balance
			processed_balance_transactions.append(bt)
		elif bt.type == "Applied To Invoice":
			processed_balance_transactions.append(bt)

	return list(reversed(processed_balance_transactions))


def get_cleaned_up_transactions(transactions: List[Dict]):
	"""Only picks Balance transactions that the users care about"""

	cleaned_up_transations = []
	for bt in transactions:
		if is_added_credits_bt(bt):
			cleaned_up_transations.append(bt)
			continue

		if bt.type == "Applied To Invoice" and not find(
			cleaned_up_transations, lambda x: x.invoice == bt.invoice
		):
			cleaned_up_transations.append(bt)
			continue
	return cleaned_up_transations


def is_added_credits_bt(bt):
	"""Returns `true` if credits were added and not some reverse transaction"""
	if not (
		bt.type == "Adjustment"
		and bt.source
		in (
			"Prepaid Credits",
			"Free Credits",
			"Transferred Credits",
		)  # Might need to re-think this
	):
		return False

	# Is not a reverse of a previous balance transaction
	bt.description = bt.description or ""
	return not bt.description.startswith("Reverse")


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
		metadata={"payment_for": "prepaid_credits"},
	)
	return {
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


@frappe.whitelist()
def create_payment_intent_for_prepaid_app(
	amount, app, payment_for, option, plan=None, subscription=None
):
	team = get_current_team(True)
	stripe = get_stripe()
	intent = stripe.PaymentIntent.create(
		amount=amount * 100,
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Prepaid App Purchase",
		metadata={
			"payment_for": payment_for,
			"payment_option": option,  # Monthly / Yearly
			"app": app,
			"plan": plan,
			"subscription": subscription,
		},
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
def get_summary():
	team = get_current_team()
	invoices = frappe.get_all(
		"Invoice",
		filters={"team": team, "status": ("in", ["Paid", "Unpaid"])},
		fields=[
			"name",
			"status",
			"period_end",
			"payment_mode",
			"type",
			"currency",
			"amount_paid",
		],
		order_by="creation desc",
	)

	invoice_names = [x.name for x in invoices]
	grouped_invoice_items = get_grouped_invoice_items(invoice_names)

	for invoice in invoices:
		invoice.items = grouped_invoice_items.get(invoice.name, [])

	return invoices


def get_grouped_invoice_items(invoices: List[str]) -> Dict:
	"""Takes a list of invoices (invoice names) and returns a dict of the form:
	{
	        "<invoice_name1>": [<invoice_items>],
	        "<invoice_name2>": [<invoice_items>],
	}
	"""
	invoice_items = frappe.get_all(
		"Invoice Item",
		filters={"parent": ("in", invoices)},
		fields=[
			"amount",
			"document_name AS name",
			"document_type AS type",
			"parent",
			"quantity",
			"rate",
			"plan",
		],
	)

	grouped_items = groupby(invoice_items, key=lambda x: x["parent"])
	invoice_items_map = {}
	for invoice_name, items in grouped_items:
		invoice_items_map[invoice_name] = list(items)

	return invoice_items_map


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


@frappe.whitelist()
def create_razorpay_order(amount):
	client = get_razorpay_client()
	team = get_current_team(get_doc=True)

	data = {
		"amount": amount * 100,
		"currency": team.currency,
		"notes": {
			"Description": "Order for Frappe Cloud Prepaid Credits",
			"Team (Frappe Cloud ID)": team.name,
		},
	}
	order = client.order.create(data=data)

	payment_record = frappe.get_doc(
		{"doctype": "Razorpay Payment Record", "order_id": order.get("id"), "team": team.name}
	).insert(ignore_permissions=True)

	return {
		"order_id": order.get("id"),
		"key_id": client.auth[0],
		"payment_record": payment_record.name,
	}


@frappe.whitelist()
def handle_razorpay_payment_success(response):
	client = get_razorpay_client()
	client.utility.verify_payment_signature(response)

	payment_record = frappe.get_doc(
		"Razorpay Payment Record",
		{"order_id": response.get("razorpay_order_id")},
		for_update=True,
	)
	payment_record.update(
		{
			"payment_id": response.get("razorpay_payment_id"),
			"signature": response.get("razorpay_signature"),
			"status": "Captured",
		}
	)
	payment_record.save(ignore_permissions=True)


@frappe.whitelist()
def handle_razorpay_payment_failed(response):
	payment_record = frappe.get_doc(
		"Razorpay Payment Record",
		{"order_id": response["error"]["metadata"].get("order_id")},
		for_update=True,
	)

	payment_record.status = "Failed"
	payment_record.failure_reason = response["error"]["description"]
	payment_record.save(ignore_permissions=True)
