# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
from __future__ import annotations

from itertools import groupby

import frappe
from frappe import _  # Import this for translation functionality
from frappe.core.utils import find
from frappe.utils import fmt_money, get_request_site_address

from press.api.regional_payments.mpesa.utils import (
	create_invoice_partner_site,
	create_payment_partner_transaction,
	fetch_param_value,
	get_details_from_request_log,
	get_mpesa_setup_for_team,
	get_payment_gateway,
	sanitize_mobile_number,
	update_tax_id_or_phone_no,
)
from press.guards import role_guard
from press.press.doctype.mpesa_setup.mpesa_connector import MpesaConnector
from press.press.doctype.team.team import (
	_enqueue_finalize_unpaid_invoices_for_team,
	has_unsettled_invoices,
)
from press.utils import get_current_team
from press.utils.billing import (
	GSTIN_FORMAT,
	clear_setup_intent,
	get_publishable_key,
	get_razorpay_client,
	get_setup_intent,
	get_stripe,
	make_formatted_doc,
	states_with_tin,
	validate_gstin_check_digit,
)
from press.utils.mpesa_utils import create_mpesa_request_log

# from press.press.doctype.paymob_callback_log.paymob_callback_log import create_payment_partner_transaction


@frappe.whitelist()
@role_guard.api("billing")
def get_publishable_key_and_setup_intent():
	team = get_current_team()
	return {
		"publishable_key": get_publishable_key(),
		"setup_intent": get_setup_intent(team),
	}


@frappe.whitelist()
@role_guard.api("billing")
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
@role_guard.api("billing")
def get_balance_credit():
	team = get_current_team(True)
	return team.get_balance()


@frappe.whitelist()
@role_guard.api("billing")
def past_invoices():
	return get_current_team(True).get_past_invoices()


@frappe.whitelist()
@role_guard.api("billing")
def invoices_and_payments():
	team = get_current_team(True)
	return team.get_past_invoices()


@frappe.whitelist()
@role_guard.api("billing")
def refresh_invoice_link(invoice):
	doc = frappe.get_doc("Invoice", invoice)
	return doc.refresh_stripe_payment_link()


@frappe.whitelist()
@role_guard.api("billing")
def balances():
	team = get_current_team()
	has_bought_credits = frappe.db.get_all(
		"Balance Transaction",
		filters={
			"source": ("in", ("Prepaid Credits", "Transferred Credits", "Free Credits")),
			"team": team,
			"docstatus": 1,
			"type": ("!=", "Partnership Fee"),
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


def get_processed_balance_transactions(transactions: list[dict]) -> list:
	"""Cleans up transactions and adjusts ending balances accordingly"""

	cleaned_up_transations = get_cleaned_up_transactions(transactions)
	processed_balance_transactions: list[dict] = []
	for bt in reversed(cleaned_up_transations):
		if is_added_credits_bt(bt) and len(processed_balance_transactions) < 1:
			processed_balance_transactions.append(bt)
		elif is_added_credits_bt(bt):
			bt["ending_balance"] = bt.get("ending_balance", 0) + processed_balance_transactions[-1].get(
				"ending_balance", 0
			)  # Adjust the ending balance
			processed_balance_transactions.append(bt)
		elif bt.get("type") == "Applied To Invoice":
			processed_balance_transactions.append(bt)

	return list(reversed(processed_balance_transactions))


def get_cleaned_up_transactions(transactions: list[dict]):
	"""Only picks Balance transactions that the users care about"""

	cleaned_up_transations = []
	for bt in transactions:
		if is_added_credits_bt(bt):
			cleaned_up_transations.append(bt)
			continue

		if bt.get("type") == "Applied To Invoice" and not find(
			cleaned_up_transations, lambda x: x.get("invoice") == bt.get("invoice")
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
@role_guard.api("billing")
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
@role_guard.api("billing")
def fetch_invoice_items(invoice):
	team = get_current_team()
	if frappe.db.get_value("Invoice", invoice, "team") != team:
		frappe.throw("Only team owners and members are permitted to download Invoice")

	return frappe.get_all(
		"Invoice Item",
		{"parent": invoice, "parenttype": "Invoice"},
		[
			"document_type",
			"document_name",
			"rate",
			"quantity",
			"amount",
			"plan",
			"description",
			"discount",
			"site",
		],
	)


@frappe.whitelist()
@role_guard.api("billing")
def get_customer_details(team):
	"""This method is called by frappe.io for creating Customer and Address"""
	team_doc = frappe.db.get_value("Team", team, "*")
	return {
		"team": team_doc,
		"address": frappe.get_doc("Address", team_doc.billing_address),
	}


@frappe.whitelist()
@role_guard.api("billing")
def create_payment_intent_for_micro_debit():
	team = get_current_team(True)
	stripe = get_stripe()

	micro_debit_charge_field = (
		"micro_debit_charge_usd" if team.currency == "USD" else "micro_debit_charge_inr"
	)
	amount = frappe.db.get_single_value("Press Settings", micro_debit_charge_field)

	intent = stripe.PaymentIntent.create(
		amount=int(amount * 100),
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Micro-Debit Card Test Charge",
		metadata={
			"payment_for": "micro_debit_test_charge",
		},
	)
	return {"client_secret": intent["client_secret"]}


@frappe.whitelist()
@role_guard.api("billing")
def create_payment_intent_for_partnership_fees():
	team = get_current_team(True)
	press_settings = frappe.get_cached_doc("Press Settings")
	metadata = {"payment_for": "partnership_fee"}
	fee_amount = press_settings.partnership_fee_usd

	if team.currency == "INR":
		fee_amount = press_settings.partnership_fee_inr
		gst_amount = fee_amount * press_settings.gst_percentage
		fee_amount += gst_amount
		metadata.update({"gst": round(gst_amount, 2)})

	stripe = get_stripe()
	intent = stripe.PaymentIntent.create(
		amount=int(fee_amount * 100),
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Partnership Fee",
		metadata=metadata,
	)
	return {
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


@frappe.whitelist()
@role_guard.api("billing")
def create_payment_intent_for_buying_credits(amount):
	team = get_current_team(True)
	metadata = {"payment_for": "prepaid_credits"}
	total_unpaid = total_unpaid_amount()

	if amount < total_unpaid and not team.erpnext_partner:
		frappe.throw(f"Amount {amount} is less than the total unpaid amount {total_unpaid}.")

	if team.currency == "INR":
		gst_amount = amount * frappe.db.get_single_value("Press Settings", "gst_percentage")
		amount += gst_amount
		metadata.update({"gst": round(gst_amount, 2)})

	amount = round(amount, 2)
	stripe = get_stripe()
	intent = stripe.PaymentIntent.create(
		amount=int(amount * 100),
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Prepaid Credits",
		metadata=metadata,
	)
	return {
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


@frappe.whitelist()
@role_guard.api("billing")
def create_payment_intent_for_prepaid_app(amount, metadata):
	stripe = get_stripe()
	team = get_current_team(True)
	payment_method = frappe.get_value(
		"Stripe Payment Method", team.default_payment_method, "stripe_payment_method_id"
	)
	try:
		if not payment_method:
			intent = stripe.PaymentIntent.create(
				amount=amount * 100,
				currency=team.currency.lower(),
				customer=team.stripe_customer_id,
				description="Prepaid App Purchase",
				metadata=metadata,
			)
		else:
			intent = stripe.PaymentIntent.create(
				amount=amount * 100,
				currency=team.currency.lower(),
				customer=team.stripe_customer_id,
				description="Prepaid App Purchase",
				off_session=True,
				confirm=True,
				metadata=metadata,
				payment_method=payment_method,
				payment_method_options={"card": {"request_three_d_secure": "any"}},
			)

		return {
			"payment_method": payment_method,
			"client_secret": intent["client_secret"],
			"publishable_key": get_publishable_key(),
		}
	except stripe.error.CardError as e:
		err = e.error
		if err.code == "authentication_required":
			# Bring the customer back on-session to authenticate the purchase
			return {
				"error": "authentication_required",
				"payment_method": err.payment_method.id,
				"amount": amount,
				"card": err.payment_method.card,
				"publishable_key": get_publishable_key(),
				"client_secret": err.payment_intent.client_secret,
			}
		if err.code:
			# The card was declined for other reasons (e.g. insufficient funds)
			# Bring the customer back on-session to ask them for a new payment method
			return {
				"error": err.code,
				"payment_method": err.payment_method.id,
				"publishable_key": get_publishable_key(),
				"client_secret": err.payment_intent.client_secret,
			}


@frappe.whitelist()
@role_guard.api("billing")
def get_payment_methods():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_payment_methods()


@frappe.whitelist()
@role_guard.api("billing")
def set_as_default(name):
	payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": get_current_team()})
	payment_method.set_default()


@frappe.whitelist()
@role_guard.api("billing")
def remove_payment_method(name):
	team = get_current_team()
	payment_method_count = frappe.db.count("Stripe Payment Method", {"team": team})

	if has_unsettled_invoices(team) and payment_method_count == 1:
		return "Unpaid Invoices"

	payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": team})
	payment_method.delete()
	return None


@frappe.whitelist()
@role_guard.api("billing")
def finalize_invoices():
	unsettled_invoices = frappe.get_all(
		"Invoice",
		{"team": get_current_team(), "status": ("in", ("Draft", "Unpaid"))},
		pluck="name",
	)

	for inv in unsettled_invoices:
		inv_doc = frappe.get_doc("Invoice", inv)
		inv_doc.finalize_invoice()


@frappe.whitelist()
@role_guard.api("billing")
def unpaid_invoices():
	team = get_current_team()
	return frappe.db.get_all(
		"Invoice",
		{
			"team": team,
			"status": ("in", ["Draft", "Unpaid", "Invoice Created"]),
			"type": "Subscription",
		},
		["name", "status", "period_end", "currency", "amount_due", "total"],
		order_by="creation asc",
	)


@frappe.whitelist()
@role_guard.api("billing")
def get_unpaid_invoices():
	team = get_current_team()
	unpaid_invoices = frappe.db.get_all(
		"Invoice",
		{
			"team": team,
			"status": "Unpaid",
			"type": "Subscription",
		},
		["name", "status", "period_end", "currency", "amount_due", "total", "stripe_invoice_url"],
		order_by="creation asc",
	)

	return unpaid_invoices  # noqa: RET504


@frappe.whitelist()
@role_guard.api("billing")
def change_payment_mode(mode):
	team = get_current_team(get_doc=True)

	team.payment_mode = mode
	if team.partner_email and mode == "Paid By Partner" and not team.billing_team:
		team.billing_team = frappe.db.get_value(
			"Team",
			{"enabled": 1, "erpnext_partner": 1, "partner_email": team.partner_email},
			"name",
		)
	if team.billing_team and mode != "Paid By Partner":
		team.billing_team = ""
	team.save()
	return


@frappe.whitelist()
@role_guard.api("billing")
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
@role_guard.api("billing")
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
@role_guard.api("billing")
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


def get_grouped_invoice_items(invoices: list[str]) -> dict:
	"""Takes a list of invoices (invoice names) and returns a dict of the form:
	{ "<invoice_name1>": [<invoice_items>], "<invoice_name2>": [<invoice_items>], }
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
@role_guard.api("billing")
def after_card_add():
	clear_setup_intent()


@frappe.whitelist()
@role_guard.api("billing")
def setup_intent_success(setup_intent, address=None):
	setup_intent = frappe._dict(setup_intent)

	# refetching the setup intent to get mandate_id from stripe
	stripe = get_stripe()
	setup_intent = stripe.SetupIntent.retrieve(setup_intent.id)

	team = get_current_team(True)
	clear_setup_intent()
	mandate_reference = setup_intent.payment_method_options.card.mandate_options.reference
	payment_method = team.create_payment_method(
		setup_intent.payment_method,
		setup_intent.id,
		setup_intent.mandate,
		mandate_reference,
		set_default=True,
		verified_with_micro_charge=True,
	)
	if address:
		address = frappe._dict(address)
		team.update_billing_details(address)

	return {"payment_method_name": payment_method.name}


@frappe.whitelist()
@role_guard.api("billing")
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
			frappe.throw("Invalid GSTIN. The input you've entered does not match the format of GSTIN.")

		tin_code = states_with_tin[address.state]
		if not address.gstin.startswith(tin_code):
			frappe.throw(f"GSTIN must start with {tin_code} for {address.state}.")

		validate_gstin_check_digit(address.gstin)


@frappe.whitelist()
@role_guard.api("billing")
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
			["amount_due", "payment_mode", "amount_due", "currency"],
			as_dict=True,
		)
		if unpaid_invoice.payment_mode == "Prepaid Credits" and team_has_balance_for_invoice(unpaid_invoice):
			return None

		return unpaid_invoice
	return None


def team_has_balance_for_invoice(prepaid_mode_invoice):
	team = get_current_team(get_doc=True)
	return team.get_balance() >= prepaid_mode_invoice.amount_due


@frappe.whitelist()
@role_guard.api("billing")
def is_paypal_enabled() -> bool:
	return frappe.db.get_single_value("Press Settings", "paypal_enabled")


@frappe.whitelist()
@role_guard.api("billing")
def create_razorpay_order(amount, transaction_type, doc_name=None) -> dict | None:
	if not transaction_type:
		frappe.throw(_("Transaction type is not set"))
	if not amount or amount <= 0:
		frappe.throw(_("Amount should be greater than zero"))

	team = get_current_team(get_doc=True)

	# transaction type validations
	_validate_razorpay_order_type(transaction_type, amount, doc_name, team.currency)

	# GST for INR transactions
	gst_amount = 0
	if team.currency == "INR":
		gst_amount = amount * frappe.db.get_single_value("Press Settings", "gst_percentage")
		amount += gst_amount

	# normalize type for payment record
	payment_record_type = (
		"Prepaid Credits" if transaction_type in ["Invoice", "Purchase Plan"] else transaction_type
	)

	amount = round(amount, 2)
	data = {
		"amount": int(amount * 100),
		"currency": team.currency,
		"notes": {
			"Description": "Order for Frappe Cloud Prepaid Credits",
			"Team (Frappe Cloud ID)": team.name,
			"gst": gst_amount,
			"Type": payment_record_type,
		},
	}

	client = get_razorpay_client()
	order = client.order.create(data=data)

	payment_record = frappe.get_doc(
		{
			"doctype": "Razorpay Payment Record",
			"order_id": order.get("id"),
			"team": team.name,
			"type": payment_record_type,
		}
	).insert(ignore_permissions=True)

	return {
		"order_id": order.get("id"),
		"key_id": client.auth[0],
		"payment_record": payment_record.name,
	}


def _validate_razorpay_order_type(transaction_type, amount, doc_name, currency):
	if transaction_type == "Prepaid Credits":
		_validate_prepaid_credits(amount, currency)
	elif transaction_type == "Purchase Plan":
		_validate_purchase_plan(amount, doc_name, currency)
	elif transaction_type == "Invoice":
		_validate_invoice_payment(amount, doc_name, currency)


def _validate_prepaid_credits(amount, currency):
	minimum_amount = 100 if currency == "INR" else 5
	if amount < minimum_amount:
		currency_symbol = "₹" if currency == "INR" else "$"
		frappe.throw(_("Amount should be at least {0}{1}").format(currency_symbol, minimum_amount))


def _validate_purchase_plan(amount, doc_name, currency):
	if not doc_name or not frappe.db.exists("Site Plan", doc_name):
		frappe.throw(_("Plan {0} does not exist").format(doc_name or ""))

	price_field = "price_inr" if currency == "INR" else "price_usd"
	plan_amount = frappe.db.get_value("Site Plan", doc_name, price_field)
	if amount < plan_amount:
		currency_symbol = "₹" if currency == "INR" else "$"
		frappe.throw(
			_("Amount should not be less than plan amount of {0}{1}").format(currency_symbol, plan_amount)
		)


def _validate_invoice_payment(amount, doc_name, currency):
	if not doc_name or not frappe.db.exists("Invoice", doc_name):
		frappe.throw(_("Invoice {0} does not exist").format(doc_name or ""))

	invoice_amount = frappe.db.get_value("Invoice", doc_name, "amount_due_with_tax")
	if amount < invoice_amount:
		currency_symbol = "₹" if currency == "INR" else "$"
		frappe.throw(
			_("Amount should not be less than invoice amount of {0}{1}").format(
				currency_symbol, invoice_amount
			)
		)


@frappe.whitelist()
@role_guard.api("billing")
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
@role_guard.api("billing")
def handle_razorpay_payment_failed(response):
	payment_record = frappe.get_doc(
		"Razorpay Payment Record",
		{"order_id": response["error"]["metadata"].get("order_id")},
		for_update=True,
	)

	payment_record.status = "Failed"
	payment_record.failure_reason = response["error"]["description"]
	payment_record.save(ignore_permissions=True)


@frappe.whitelist()
@role_guard.api("billing")
def total_unpaid_amount():
	team = get_current_team(get_doc=True)
	balance = team.get_balance()
	negative_balance = -1 * balance if balance < 0 else 0


	try:
		return (
			frappe.get_all(
				"Invoice",
				{"status": "Unpaid", "team": team.name, "type": "Subscription", "docstatus": ("!=", 2)},
				["sum(`amount_due`) as total"],
				pluck="total",
			)[0]
			or 0
		) + negative_balance
	except:  # noqa E722
		return (
			frappe.get_all(
				"Invoice",
				{"status": "Unpaid", "team": team.name, "type": "Subscription", "docstatus": ("!=", 2)},
				[{"SUM": "amount_due", "as": "total"}],
				pluck="total",
			)[0]
			or 0
		) + negative_balance


@frappe.whitelist()
@role_guard.api("billing")
def get_current_billing_amount():
	team = get_current_team(get_doc=True)
	due_date = frappe.utils.get_last_day(frappe.utils.getdate())

	return (
		frappe.get_value(
			"Invoice",
			{"team": team.name, "due_date": due_date, "docstatus": 0},
			"total",
		)
		or 0
	)


# Mpesa integrations, mpesa express
"""Send stk push to the user"""


def generate_stk_push(**kwargs):
	"""Generate stk push by making a API call to the stk push API."""
	args = frappe._dict(kwargs)
	partner_value = args.partner

	# Fetch the team document based on the extracted partner value
	partner = frappe.get_all("Team", filters={"user": partner_value, "erpnext_partner": 1}, pluck="name")
	if not partner:
		frappe.throw(_(f"Partner team {partner_value} not found"), title=_("Mpesa Express Error"))

	# Get Mpesa settings for the partner's team
	mpesa_setup = get_mpesa_setup_for_team(partner[0])
	try:
		callback_url = (
			get_request_site_address(True) + "/api/method/press.api.billing.verify_m_pesa_transaction"
		)
		env = "production" if not mpesa_setup.sandbox else "sandbox"
		# for sandbox, business shortcode is same as till number
		business_shortcode = (
			mpesa_setup.business_shortcode if env == "production" else mpesa_setup.till_number
		)
		connector = MpesaConnector(
			env=env,
			app_key=mpesa_setup.consumer_key,
			app_secret=mpesa_setup.get_password("consumer_secret"),
		)

		mobile_number = sanitize_mobile_number(args.sender)
		response = connector.stk_push(
			business_shortcode=business_shortcode,
			amount=args.amount_with_tax,
			passcode=mpesa_setup.get_password("pass_key"),
			callback_url=callback_url,
			reference_code=mpesa_setup.till_number,
			phone_number=mobile_number,
			description="Frappe Cloud Payment",
		)
		return response  # noqa: RET504

	except Exception:
		frappe.log_error("Mpesa Express Transaction Error")
		frappe.throw(
			_("Issue detected with Mpesa configuration, check the error logs for more details"),
			title=_("Mpesa Express Error"),
		)


@frappe.whitelist(allow_guest=True)
def verify_m_pesa_transaction(**kwargs):
	"""Verify the transaction result received via callback from STK."""
	transaction_response, request_id = parse_transaction_response(kwargs)
	status = handle_transaction_result(transaction_response, request_id)

	return {"status": status, "ResultDesc": transaction_response.get("ResultDesc")}


def parse_transaction_response(kwargs):
	"""Parse and validate the transaction response."""

	if "Body" not in kwargs or "stkCallback" not in kwargs["Body"]:
		frappe.log_error(title="Invalid transaction response format", message=kwargs)
		frappe.throw(_("Invalid transaction response format"))

	transaction_response = frappe._dict(kwargs["Body"]["stkCallback"])
	checkout_id = getattr(transaction_response, "CheckoutRequestID", "")
	if not isinstance(checkout_id, str):
		frappe.throw(_("Invalid Checkout Request ID"))

	return transaction_response, checkout_id


def handle_transaction_result(transaction_response, integration_request):
	"""Handle the logic based on ResultCode in the transaction response."""

	result_code = transaction_response.get("ResultCode")
	status = None

	if result_code == 0:
		try:
			status = "Completed"
			create_mpesa_request_log(
				transaction_response, "Host", "Mpesa Express", integration_request, None, status
			)

			create_mpesa_payment_record(transaction_response)
		except Exception as e:
			frappe.log_error(f"Mpesa: Transaction failed with error {e}")

	elif result_code == 1037:  # User unreachable (Phone off or timeout)
		status = "Failed"
		create_mpesa_request_log(
			transaction_response, "Host", "Mpesa Express", integration_request, None, status
		)
		frappe.log_error("Mpesa: User cannot be reached (Phone off or timeout)")

	elif result_code == 1032:  # User cancelled the request
		status = "Cancelled"
		create_mpesa_request_log(
			transaction_response, "Host", "Mpesa Express", integration_request, None, status
		)
		frappe.log_error("Mpesa: Request cancelled by user")

	else:  # Other failure codes
		status = "Failed"
		create_mpesa_request_log(
			transaction_response, "Host", "Mpesa Express", integration_request, None, status
		)
		frappe.log_error(f"Mpesa: Transaction failed with ResultCode {result_code}")
	return status


@frappe.whitelist()
@role_guard.api("billing")
def request_for_payment(**kwargs):
	"""request for payments"""
	team = get_current_team()

	kwargs.setdefault("team", team)
	args = frappe._dict(kwargs)
	update_tax_id_or_phone_no(team, args.tax_id, args.phone_number)

	amount = args.request_amount
	args.request_amount = frappe.utils.rounded(amount, 2)
	response = frappe._dict(generate_stk_push(**args))
	handle_api_mpesa_response("CheckoutRequestID", args, response)

	return response


def handle_api_mpesa_response(global_id, request_dict, response):
	"""Response received from API calls returns a global identifier for each transaction, this code is returned during the callback."""
	# check error response
	if response.requestId:
		req_name = response.requestId
		error = response
	else:
		# global checkout id used as request name
		req_name = getattr(response, global_id)
		error = None

	create_mpesa_request_log(request_dict, "Host", "Mpesa Express", req_name, error, output=response)

	if error:
		frappe.throw(_(response.errorMessage), title=_("Transaction Error"))


def create_mpesa_payment_record(transaction_response):
	"""Create a new entry in the Mpesa Payment Record for a successful transaction."""
	item_response = transaction_response.get("CallbackMetadata", {}).get("Item", [])
	mpesa_receipt_number = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
	transaction_time = fetch_param_value(item_response, "TransactionDate", "Name")
	phone_number = fetch_param_value(item_response, "PhoneNumber", "Name")
	transaction_id = transaction_response.get("CheckoutRequestID")
	amount = fetch_param_value(item_response, "Amount", "Name")
	merchant_request_id = transaction_response.get("MerchantRequestID")
	info = get_details_from_request_log(transaction_id)
	gateway_name = get_payment_gateway(info.partner)
	# Create a new entry in M-Pesa Payment Record
	data = {
		"transaction_id": transaction_id,
		"amount": amount,
		"team": frappe.get_value("Team", info.team, "user"),
		"tax_id": frappe.get_value("Team", info.team, "mpesa_tax_id"),
		"default_currency": "KES",
		"rate": info.requested_amount,
	}
	if frappe.db.exists("Mpesa Payment Record", {"transaction_id": transaction_id}):
		return

	try:
		mpesa_invoice, invoice_name = create_invoice_partner_site(data, gateway_name)
	except Exception as e:
		frappe.log_error(f"Failed to create mpesa invoice on partner site: {e}")
		mpesa_invoice = invoice_name = None

	try:
		payment_record = frappe.get_doc(
			{
				"doctype": "Mpesa Payment Record",
				"transaction_id": transaction_id,
				"transaction_time": parse_datetime(transaction_time),
				"transaction_type": "Mpesa Express",
				"team": info.team,
				"phone_number": str(phone_number),
				"amount": info.requested_amount,
				"grand_total": amount,
				"merchant_request_id": merchant_request_id,
				"payment_partner": info.partner,
				"amount_usd": info.amount_usd,
				"exchange_rate": info.exchange_rate,
				"local_invoice": mpesa_invoice,
				"mpesa_receipt_number": mpesa_receipt_number,
			}
		)
		payment_record.insert(ignore_permissions=True)
		payment_record.submit()
	except Exception:
		frappe.log_error("Failed to create Mpesa Payment Record")
		raise
	"""create payment partner transaction which will then create balance transaction"""
	create_payment_partner_transaction(
		info.team, info.partner, info.exchange_rate, info.amount_usd, info.requested_amount, gateway_name
	)
	mpesa_details = {
		"mpesa_receipt_number": mpesa_receipt_number,
		"mpesa_merchant_id": merchant_request_id,
		"mpesa_payment_record": payment_record.name,
		"mpesa_request_id": transaction_id,
		"mpesa_invoice": invoice_name,
	}
	create_balance_transaction_and_invoice(info.team, info.amount_usd, mpesa_details)

	frappe.msgprint(_("Mpesa Payment Record entry created successfully"))


def create_balance_transaction_and_invoice(team, amount, mpesa_details):
	try:
		balance_transaction = frappe.get_doc(
			doctype="Balance Transaction",
			team=team,
			source="Prepaid Credits",
			type="Adjustment",
			amount=amount,
			description=mpesa_details.get("mpesa_payment_record"),
			paid_via_local_pg=1,
		)
		balance_transaction.insert(ignore_permissions=True)
		balance_transaction.submit()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team,
			type="Prepaid Credits",
			status="Paid",
			total=amount,
			amount_due=amount,
			amount_paid=amount,
			amount_due_with_tax=amount,
			due_date=frappe.utils.nowdate(),
			mpesa_merchant_id=mpesa_details.get("mpesa_merchant_id", ""),
			mpesa_receipt_number=mpesa_details.get("mpesa_receipt_number", ""),
			mpesa_request_id=mpesa_details.get("mpesa_request_id", ""),
			mpesa_payment_record=mpesa_details.get("mpesa_payment_record", ""),
			mpesa_invoice=mpesa_details.get("mpesa_invoice", ""),
		)
		invoice.append(
			"items",
			{
				"description": "Prepaid Credits",
				"document_type": "Balance Transaction",
				"document_name": balance_transaction.name,
				"quantity": 1,
				"rate": amount,
			},
		)
		invoice.insert(ignore_permissions=True)
		invoice.submit()

		_enqueue_finalize_unpaid_invoices_for_team(team)
	except Exception:
		frappe.log_error("Mpesa: Failed to create balance transaction and invoice")


def parse_datetime(date):
	from datetime import datetime

	return datetime.strptime(str(date), "%Y%m%d%H%M%S")


@frappe.whitelist()
@role_guard.api("billing")
def billing_forecast():
	"""
	Get billing forecast and breakdown data for the current month.
	"""
	team = get_current_team(True)

	# Get dates and related info
	date_info = _get_date_context()

	# Get last and current month invoice currency and totals
	invoice_data = _get_invoice_data(team.name, date_info)

	# Calculate month-end forecast amount and per-service breakdown of forecasts
	forecast_data = _calculate_forecast_data(team.name, team.currency, date_info)

	# Get usage breakdowns for last month, current month-to-date and forecasted month-end
	usage_breakdown = _get_usage_data_breakdown(invoice_data, forecast_data, date_info["days_remaining"])

	# Calculate month-over-month and month-to-date % changes
	changes = _calculate_percentage_changes(
		team.name, invoice_data, forecast_data["forecasted_total"], date_info
	)

	return {
		"current_month_to_date_cost": invoice_data["current_month_total"],
		"forecasted_month_end": forecast_data["forecasted_total"],
		"last_month_cost": invoice_data["last_month_total"],
		"usage_breakdown": usage_breakdown,
		"month_over_month_change": changes["month_over_month"],
		"mtd_change": changes["mtd_change"],
		"currency": team.currency,
	}


def _get_date_context():
	"""Get all date-related data in one place for billing forecast."""
	from frappe.utils import add_days, add_months, get_last_day, getdate

	current_date = getdate()
	current_month_start = current_date.replace(day=1)
	current_month_end = get_last_day(current_date)
	last_month_end = add_days(current_month_start, -1)
	last_month_start = last_month_end.replace(day=1)
	last_month_same_date = add_months(current_date, -1)

	days_in_month = (current_month_end - current_month_start).days + 1
	days_passed = (current_date - current_month_start).days + 1
	days_remaining = max(days_in_month - days_passed, 0)

	return {
		"current_date": current_date,
		"current_month_start": current_month_start,
		"current_month_end": current_month_end,
		"last_month_start": last_month_start,
		"last_month_end": last_month_end,
		"last_month_same_date": last_month_same_date,
		"days_in_month": days_in_month,
		"days_passed": days_passed,
		"days_remaining": days_remaining,
	}


def _get_invoice_data(team_name: str, date_info: dict):
	"""Get current and last month invoice data."""
	current_invoice = _get_invoice_based_on_due_date(team_name, date_info["current_month_end"])
	last_month_invoice = _get_invoice_based_on_due_date(team_name, date_info["last_month_end"])

	return {
		"current_invoice": current_invoice,
		"last_month_invoice": last_month_invoice,
		"current_month_total": current_invoice.total if current_invoice else 0,
		"last_month_total": last_month_invoice.total if last_month_invoice else 0,
	}


def _get_invoice_based_on_due_date(team_name, due_date):
	return frappe.db.get_value(
		"Invoice",
		{"team": team_name, "due_date": due_date, "docstatus": ("!=", 2)},
		["name", "total", "currency"],
		as_dict=True,
	)


def _calculate_forecast_data(
	team: str, currency: str, date_info: dict
) -> dict[str, float | dict[str, float]]:
	"""Calculate monthly total cost of all active subscriptions and forecasted cost for remaining days in the month"""
	from frappe.utils import flt

	subscriptions = _get_active_subscriptions(team)
	days_remaining = date_info["days_remaining"]
	days_in_month = date_info["days_in_month"]

	forecasted_month_end = 0
	per_service_forecast: dict[str, float] = {}  # Forecasted remaining cost per service

	price_field = "price_usd" if currency == "USD" else "price_inr"

	for sub in subscriptions:
		plan = frappe.db.get_value(sub.plan_type, sub.plan, [price_field], as_dict=True)
		if not plan:
			continue

		price = plan.get(price_field, 0)
		if price > 0:
			forecasted_month_end += price

			# Forecasted remaining cost for this service
			if days_remaining > 0:
				remaining_cost = (price / days_in_month) * days_remaining
				per_service_forecast[sub.document_type] = flt(
					per_service_forecast.get(sub.document_type, 0) + remaining_cost
				)

	return {
		"forecasted_total": forecasted_month_end,
		"subscription_forecast": per_service_forecast,
	}


def _get_active_subscriptions(team: str):
	"""Get all active subscriptions for a team."""
	Subscription = frappe.qb.DocType("Subscription")

	return (
		frappe.qb.from_(Subscription)
		.select(Subscription.document_type, Subscription.plan_type, Subscription.plan)
		.where((Subscription.team == team) & (Subscription.enabled == 1))
		.run(as_dict=True)
	)


def _get_usage_data_breakdown(invoice_data: dict, forecast_data: dict, days_remaining: int = 0):
	"""Get usage breakdown grouped by document_type."""
	current_breakdown = (
		_get_usage_breakdown(invoice_data["current_invoice"].name) if invoice_data["current_invoice"] else {}
	)
	last_month_breakdown = (
		_get_usage_breakdown(invoice_data["last_month_invoice"].name)
		if invoice_data["last_month_invoice"]
		else {}
	)
	forecasted_breakdown = _get_forecasted_usage_breakdown(
		current_breakdown, forecast_data["subscription_forecast"], days_remaining
	)

	return {
		"month_to_date_usage_breakdown": current_breakdown,
		"last_month_usage_breakdown": last_month_breakdown,
		"forecasted_usage_breakdown": forecasted_breakdown,
	}


def _get_usage_breakdown(invoice: str) -> dict[str, float]:
	if not invoice:
		return {}

	invoice_doc = frappe.get_doc("Invoice", invoice)
	service_costs: dict[str, float] = {}

	for item in invoice_doc.items:
		service = item.document_type
		service_costs[service] = service_costs.get(service, 0.0) + float(item.amount)

	return service_costs


def _get_forecasted_usage_breakdown(
	current_usage: dict, subscription_forecast: dict, days_remaining: int
) -> dict:
	# Consider usage so far as well as active subscriptions to forecast month-end usage breakdown
	if not subscription_forecast and not current_usage:
		return {}

	if days_remaining == 0:  # if end of month, use actual usage
		return current_usage

	forecasted_usage_breakdown = {}
	for service in set(list(current_usage.keys()) + list(subscription_forecast.keys())):
		forecasted_usage_breakdown[service] = current_usage.get(service, 0) + subscription_forecast.get(
			service, 0
		)

	return forecasted_usage_breakdown


def _calculate_percentage_changes(team_name: str, invoice_data: dict, forecasted_total, date_info: dict):
	"""Calculate month-over-month and MTD changes."""
	from frappe.utils import flt

	# Month-over-month change
	month_over_month_change = 0
	last_month_total = invoice_data["last_month_total"]
	if last_month_total > 0:
		month_over_month_change = (forecasted_total - last_month_total) / last_month_total * 100

	# Month-to-date change
	mtd_change = _calculate_mtd_change(
		team_name,
		invoice_data["current_month_total"],
		date_info["last_month_start"],
		date_info["last_month_same_date"],
	)

	return {
		"month_over_month": flt(month_over_month_change, 2),
		"mtd_change": flt(mtd_change, 2),
	}


def _calculate_mtd_change(team: str, current_mtd_cost: float, last_month_start, last_month_same_date):
	from frappe.utils import flt

	last_mtd_total = _get_usage_records_total_for_date_range(team, last_month_start, last_month_same_date)

	mtd_change = 0
	if last_mtd_total > 0:
		mtd_change = ((current_mtd_cost - last_mtd_total) / last_mtd_total) * 100
	return flt(mtd_change, 2)


def _get_usage_records_total_for_date_range(team: str, start_date, end_date):
	"""Get total amount from Usage Records for a team in a date range."""
	from frappe.query_builder.functions import Sum

	UsageRecord = frappe.qb.DocType("Usage Record")
	total_amount = (
		frappe.qb.from_(UsageRecord)
		.select(Sum(UsageRecord.amount))
		.where(
			(UsageRecord.team == team)
			& (UsageRecord.date >= start_date)
			& (UsageRecord.date <= end_date)
			& (UsageRecord.docstatus == 1)
		)
		.run(pluck=True)
	)

	return total_amount[0] or 0
