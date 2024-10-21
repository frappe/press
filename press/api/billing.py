# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from itertools import groupby
from typing import Dict, List


import frappe
from frappe.core.utils import find
from frappe.utils import fmt_money
import json 

import frappe
from frappe.query_builder import DocType

from press.press.doctype.team.team import (
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
from frappe.utils import get_request_site_address
from press.press.doctype.mpesa_settings.mpesa_connector import MpesaConnector
from json import dumps, loads
from frappe.integrations.utils import create_request_log
from frappe import _  # Import this for translation functionality
import json
import requests
from frappe.utils.password import get_decrypted_password


# other imports and the rest of your code...


supported_mpesa_currencies = ["KES"]

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
def get_balance_credit():
	team = get_current_team(True)
	return team.get_balance()


@frappe.whitelist()
def past_invoices():
	return get_current_team(True).get_past_invoices()


@frappe.whitelist()
def invoices_and_payments():
	team = get_current_team(True)
	invoices = team.get_past_invoices()
	return invoices


@frappe.whitelist()
def refresh_invoice_link(invoice):
	doc = frappe.get_doc("Invoice", invoice)
	return doc.refresh_stripe_payment_link()


@frappe.whitelist()
def balances():
	team = get_current_team()
	has_bought_credits = frappe.db.get_all(
		"Balance Transaction",
		filters={
			"source": ("in", ("Prepaid Credits", "Transferred Credits", "Free Credits")),
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
def create_payment_intent_for_micro_debit(payment_method_name):
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
			"payment_method_name": payment_method_name,
		},
	)
	return {"client_secret": intent["client_secret"]}


@frappe.whitelist()
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
		elif err.code:
			# The card was declined for other reasons (e.g. insufficient funds)
			# Bring the customer back on-session to ask them for a new payment method
			return {
				"error": err.code,
				"payment_method": err.payment_method.id,
				"publishable_key": get_publishable_key(),
				"client_secret": err.payment_intent.client_secret,
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
	team = get_current_team()
	payment_method_count = frappe.db.count("Stripe Payment Method", {"team": team})

	if has_unsettled_invoices(team) and payment_method_count == 1:
		return "Unpaid Invoices"

	payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": team})
	payment_method.delete()


@frappe.whitelist()
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
def unpaid_invoices():
	team = get_current_team()
	invoices = frappe.get_all(
		"Invoice",
		{
			"team": team,
			"status": ("in", ["Draft", "Unpaid", "Invoice Created"]),
			"type": "Subscription",
		},
		["name", "status", "period_end", "currency", "amount_due", "total"],
		order_by="creation asc",
	)

	return invoices


@frappe.whitelist()
def change_payment_mode(mode):
	team = get_current_team(get_doc=True)
	unpaid_invoices = frappe.get_all(
		"Invoice",
		{"team": team.name, "status": ("in", ["Draft", "Unpaid"]), "type": "Subscription"},
	)
	if unpaid_invoices and mode == "Paid By Partner":
		return "Unpaid Invoices"

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
def after_card_add():
	clear_setup_intent()


@frappe.whitelist()
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
	)
	if address:
		address = frappe._dict(address)
		team.update_billing_details(address)

	return {"payment_method_name": payment_method.name}


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
			["amount_due", "payment_mode", "amount_due", "currency"],
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
def create_razorpay_order(amount):
	client = get_razorpay_client()
	team = get_current_team(get_doc=True)

	if team.currency == "INR":
		gst_amount = amount * frappe.db.get_single_value("Press Settings", "gst_percentage")
		amount += gst_amount

	amount = round(amount, 2)
	data = {
		"amount": int(amount * 100),
		"currency": team.currency,
		"notes": {
			"Description": "Order for Frappe Cloud Prepaid Credits",
			"Team (Frappe Cloud ID)": team.name,
			"gst": gst_amount if team.currency == "INR" else 0,
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


@frappe.whitelist()
def total_unpaid_amount():
	team = get_current_team(get_doc=True)
	balance = team.get_balance()
	negative_balance = -1 * balance if balance < 0 else 0

	return (
		frappe.get_all(
			"Invoice",
			{"status": "Unpaid", "team": team.name, "type": "Subscription"},
			["sum(amount_due) as total"],
			pluck="total",
		)[0]
		or 0
	) + negative_balance

#Mpesa integrations, mpesa express
def validate_mpesa_transaction_currency(currency):
	if currency not in supported_mpesa_currencies:
		frappe.throw(
			_(
				"Please select another payment method. Mpesa does not support transactions in currency '{0}'"
			).format(currency)
		)
  
  
'''ensures number take the right format'''
def sanitize_mobile_number(number):
	"""Add country code and strip leading zeroes from the phone number."""
	return "254" + str(number).lstrip("0")

'''split amount if it exceeds 150,000'''
def split_request_amount_according_to_transaction_limit(amount, transaction_limit):
		request_amount = amount
		if request_amount > transaction_limit:
			# make multiple requests
			request_amounts = []
			requests_to_be_made = frappe.utils.ceil(
				request_amount / transaction_limit
			)  # 480/150 = ceil(3.2) = 4
			for i in range(requests_to_be_made):
				amount = transaction_limit
				if i == requests_to_be_made - 1:
					amount = request_amount - (
						transaction_limit * i
					)  # for 4th request, 480 - (150 * 3) = 30
				request_amounts.append(amount)
		else:
			request_amounts = [request_amount]

		return request_amounts

'''Send stk push to the user'''
def generate_stk_push(**kwargs):
	"""Generate stk push by making a API call to the stk push API."""
	args = frappe._dict(kwargs)
	partner_value = args.partner
	
	# Fetch the team document based on the extracted partner value
	partner_ = frappe.get_all("Team", filters={"user": partner_value}, pluck="name")
	if not partner_:
		frappe.throw(_("Partner not found"), title=_("Mpesa Express Error"))
	partner = frappe.get_doc("Team", partner_[0])	
	
	# Get Mpesa settings for the partner's team
	mpesa_settings = get_mpesa_settings_for_team(partner.name)
	try:
		callback_url = (
			#get_request_site_address(True)
			"https://9876-41-80-113-21.ngrok-free.app"+ "/api/method/press.api.billing.verify_mpesa_transaction"
		)

		env = "production" if not mpesa_settings.sandbox else "sandbox"
		# for sandbox, business shortcode is same as till number
		business_shortcode = (
			mpesa_settings.business_shortcode if env == "production" else mpesa_settings.till_number
		)

		connector = MpesaConnector(
			env=env,
			app_key=mpesa_settings.consumer_key,
			app_secret=mpesa_settings.get_password("consumer_secret"),
		)

		mobile_number = sanitize_mobile_number(args.sender)
		response = connector.stk_push(
			business_shortcode=business_shortcode,
			amount= 1, #args.request_amount,
			passcode=mpesa_settings.get_password("online_passkey"),
			callback_url=callback_url,
			reference_code=mpesa_settings.till_number,
			phone_number=mobile_number,
			description="Frappe Cloud Payment",
		)
		return response

	except Exception:
		frappe.log_error("Mpesa Express Transaction Error")
		frappe.throw(
			_("Issue detected with Mpesa configuration, check the error logs for more details"),
			title=_("Mpesa Express Error"),
		)

def get_mpesa_settings_for_team(team_name):
	"""Fetch Mpesa settings for a given team."""
	
	mpesa_settings = frappe.get_all("Mpesa Settings", filters={"team": team_name}, pluck="name")
	if not mpesa_settings:
		frappe.throw(_("Mpesa Settings not configured for this team"), title=_("Mpesa Express Error"))
	return frappe.get_doc("Mpesa Settings", mpesa_settings[0])
  

@frappe.whitelist(allow_guest=True)
def verify_mpesa_transaction(**kwargs):
    """Verify the transaction result received via callback from STK."""    
    transaction_response, integration_request = parse_transaction_response(kwargs)    
    handle_transaction_result(transaction_response, integration_request)
    save_integration_request(integration_request)

    return {
        "status": integration_request.status,
        "ResultDesc": transaction_response.get("ResultDesc")
    }


def parse_transaction_response(kwargs):
    """Parse and validate the transaction response."""
    
    if "Body" not in kwargs or "stkCallback" not in kwargs["Body"]:
        frappe.throw(_("Invalid transaction response format"))
    transaction_response = frappe._dict(kwargs["Body"]["stkCallback"])
    checkout_id = getattr(transaction_response, "CheckoutRequestID", "")
    if not isinstance(checkout_id, str):
        frappe.throw(_("Invalid Checkout Request ID"))

    # Retrieve the corresponding Integration Request document
    integration_request = frappe.get_doc("Integration Request", checkout_id)
    
    return transaction_response, integration_request


def handle_transaction_result(transaction_response, integration_request):
    """Handle the logic based on ResultCode in the transaction response."""

    result_code = transaction_response.get("ResultCode")

    if result_code == 0:
        try:
            integration_request.handle_success(transaction_response)
            create_mpesa_payment_register_entry(transaction_response)
            integration_request.status = "Completed"
        except Exception:
            integration_request.handle_failure(transaction_response)
            frappe.log_error("Mpesa: Failed to verify transaction")
    elif result_code == 1037:  # User unreachable (Phone off or timeout)
        integration_request.handle_failure(transaction_response)
        integration_request.status = "Failed"
        frappe.log_error("Mpesa: User cannot be reached (Phone off or timeout)")
    elif result_code == 1032:  # User cancelled the request
        integration_request.handle_failure(transaction_response)
        integration_request.status = "Cancelled"
        frappe.log_error("Mpesa: Request cancelled by user")
    else:  # Other failure codes
        integration_request.handle_failure(transaction_response)
        integration_request.status = "Failed"
        frappe.log_error(f"Mpesa: Transaction failed with ResultCode {result_code}")


def save_integration_request(integration_request):
    """Save and commit the changes to the Integration Request."""
    integration_request.save(ignore_permissions=True)
    frappe.db.commit()


'''fetch parameters from the args'''
def fetch_param_value(response, key, key_field):
	"""Fetch the specified key from list of dictionary. Key is identified via the key field."""
	for param in response:
		if param[key_field] == key:
			return param["Value"]

'''get completed integration requests'''
def get_completed_integration_requests_info(reference_doctype, reference_docname, checkout_id):
	output_of_other_completed_requests = frappe.get_all(
		"Integration Request",
		filters={
			"name": ["!=", checkout_id],
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
			"status": "Completed",
		},
		pluck="output",
	)

	mpesa_receipts, completed_payments = [], []

	for out in output_of_other_completed_requests:
		out = frappe._dict(loads(out))
		item_response = out["CallbackMetadata"]["Item"]
		completed_amount = fetch_param_value(item_response, "Amount", "Name")
		completed_mpesa_receipt = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
		completed_payments.append(completed_amount)
		mpesa_receipts.append(completed_mpesa_receipt)

	return mpesa_receipts, completed_payments

'''request for payments'''
@frappe.whitelist(allow_guest=True)
#def request_for_payment(**kwargs)
def request_for_payment(**kwargs):
	kwargs.setdefault("reference_doctype", "Invoice")
	kwargs.setdefault("reference_docname", "INV-2024-00006")
	kwargs.setdefault("transaction_limit", 150000)
	kwargs.setdefault('team', 'Administrator')
	args = frappe._dict(kwargs)
	update_tax_id(args.team, args.tax_id)
	request_amounts = split_request_amount_according_to_transaction_limit(args.request_amount, args.transaction_limit)
	for i, amount in enumerate(request_amounts):
		args.request_amount = amount
		if frappe.flags.in_test:
			from press.press.doctype.mpesa_settings.test_mpesa_settings import (
				get_payment_request_response_payload,
			)

			response = frappe._dict(get_payment_request_response_payload(amount))
		else:
			response = frappe._dict(generate_stk_push(**args))
			
		handle_api_mpesa_response("CheckoutRequestID", args, response)
	return response

def get_payment_gateway(partner_value):
	"""Get the payment gateway for the partner."""
	partner = frappe.get_doc("Team", partner_value)	
	# Get Mpesa settings for the partner's team
	mpesa_settings = get_mpesa_settings_for_team(partner.name)
	payment_gateway = frappe.get_all("Payment Gateway", filters={"gateway_settings":"Mpesa Settings", "gateway_controller":mpesa_settings.name}, pluck="name")
	if not payment_gateway:
		frappe.throw(_("Payment Gateway not found"), title=_("Mpesa Express Error"))
	gateway=frappe.get_doc("Payment Gateway", payment_gateway[0])
	return gateway.name
 
def handle_api_mpesa_response(global_id, request_dict, response):
		"""Response received from API calls returns a global identifier for each transaction, this code is returned during the callback."""
		# check error response
		if getattr(response, "requestId"):
			req_name = getattr(response, "requestId")
			error = response
		else:
			# global checkout id used as request name
			req_name = getattr(response, global_id)
			error = None

		if not frappe.db.exists("Integration Request", req_name):
			create_request_log(request_dict, "Host", "Mpesa Express", req_name, error)

		if error:
			frappe.throw(_(getattr(response, "errorMessage")), title=_("Transaction Error"))
   
def create_mpesa_payment_register_entry(transaction_response):
	"""Create a new entry in the Mpesa Payment Record for a successful transaction."""
	# Extract necessary details from the transaction response
	item_response = transaction_response.get("CallbackMetadata", {}).get("Item", [])
	
	# Fetch relevant details from the response
	transaction_id = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
	trans_time = fetch_param_value(item_response, "TransactionDate", "Name")
	msisdn = fetch_param_value(item_response, "PhoneNumber", "Name")
	transaction_id=transaction_response.get("CheckoutRequestID")
	amount = fetch_param_value(item_response, "Amount", "Name")
	request_id=transaction_response.get("MerchantRequestID")
	team, partner = get_team_and_partner_from_integration_request(transaction_id)
	amount_usd, exchange_rate=convert("USD", "KES", amount)
	gateway_name=get_payment_gateway(partner) 	
	
	# Create a new entry in M-Pesa Payment Record
	data={
	"transaction_id": transaction_id,
	"trans_amount": amount,
	"team": "Sales Team",
	"default_currency": "KES"
}
	new_entry = frappe.get_doc({
		"doctype": "Mpesa Payment Record",
		"transaction_id": transaction_id,
		"trans_time": trans_time,
		"transaction_type":"Mpesa Express",
		"team": team,
		"msisdn": msisdn,
		"trans_amount": amount,
		"merchant_request_id": request_id,
		"payment_partner": partner,
		"amount_usd": amount_usd,
		"exchange_rate": exchange_rate,
		"payment_partner":partner,
		"local_invoice":create_invoice_partner_site(data, gateway_name),
	})
 	
	print("Hello mokimo")
	new_entry.insert(ignore_permissions=True)
	new_entry.submit()
	frappe.db.commit()  
	frappe.msgprint(_("Mpesa Payment Record entry created successfully"))
	
	
def create_balance_transaction(team, amount, invoice=None):
	"""Create a new entry in the Balance Transaction table."""
 
	# Get the ending balance of this team
	team_balance_transaction = frappe.get_all(
		"Balance Transaction", 
		filters={"team": team}, 
		fields=["ending_balance"], 
		order_by="creation desc", 
		limit=1
	)
	ending_balance = team_balance_transaction[0].ending_balance if team_balance_transaction else 0

	# Create a new entry in the Balance Transaction table
	new_entry = frappe.get_doc({
		"doctype": "Balance Transaction",
		"team": team,
		"type": "Adjustment",
		"amount": amount,
		"source": "Prepaid Credits",
		"ending_balance": ending_balance + amount,
		"docstatus": 1,
		"invoice": invoice if invoice else None,
		"description": "Added Credits through mpesa payments",
	})

	new_entry.insert(ignore_permissions=True)
	frappe.db.commit()  
	frappe.msgprint(_("Balance Transaction entry created successfully"))

	return new_entry.name 

 
def after_save_mpesa_payment_record(doc, method=None):
	try:
		team = doc.team
		amount = doc.amount_usd
		
		balance_transaction_name = create_balance_transaction(team, amount)
		
		frappe.db.set_value('Mpesa Payment Record', doc.name, 'balance_transaction', balance_transaction_name)
		
		frappe.db.set_value('Mpesa Payment Record', doc.name, 'docstatus', 1)
		doc.reload()
		frappe.db.commit()
		
		frappe.msgprint(_("Mpesa Payment Record has been linked with Balance Transaction and submitted."))
	except Exception as e:
		frappe.throw(_("An error occurred: ") + str(e))
		frappe.log_error(message=str(e), title="Mpesa Payment Submission Failed")


def get_team_and_partner_from_integration_request(transaction_id):
	"""Get the team and partner associated with the integration request."""
	integration_request = frappe.get_doc("Integration Request", transaction_id)
	request_data = integration_request.data
	# Parse the request_data as a dictionary
	if request_data:
		try:
			request_data_dict = json.loads(request_data)  
			team_ = request_data_dict.get("team")
			team = frappe.get_value("Team", {"user": team_}, "name")
			partner_ = request_data_dict.get("partner")
			partner = frappe.get_value("Team", {"user": partner_}, "name")
		except json.JSONDecodeError:
			frappe.throw(_("Invalid JSON format in request_data"))
			team = None
			partner = None
	else:
		team = None
		partner = None
	
	return team, partner

@frappe.whitelist(allow_guest=True)
def display_mpesa_payment_partners():
	"""Display the list of partners in the system with Mpesa integration enabled."""
	
	Team = DocType("Team")
	MpesaSettings = DocType("Mpesa Settings")

	query = (
		frappe.qb.from_(Team)
		.join(MpesaSettings)
		.on(Team.name == MpesaSettings.team)
		.select(Team.user)
		.where((Team.country == "Kenya") & (MpesaSettings.sandbox == 1))
	)

	mpesa_partners = query.run(as_dict=True)

	return [partner['user'] for partner in mpesa_partners]

@frappe.whitelist(allow_guest=True)
def get_tax_percentage(payment_partner):
	team_doc = frappe.get_doc("Team", {"user": payment_partner})
	mpesa_settings=frappe.get_all("Mpesa Settings", filters={"api_type":"Mpesa Express", "team":team_doc.name}, fields=["name"])
	for mpesa_setting in mpesa_settings:
		payment_gateways = frappe.get_all("Payment Gateway", filters={"gateway_settings":"Mpesa settings","gateway_controller":mpesa_setting }, fields=["taxes_and_charges"])
		if payment_gateways:
			taxes_and_charges = payment_gateways[0].taxes_and_charges
	return taxes_and_charges
	
def convert(from_currency, to_currency, amount):
	"""Convert the given amount from one currency to another."""
	exchange_rate = frappe.get_value("Currency Exchange", {"from_currency": from_currency, "to_currency": to_currency}, "exchange_rate")
	converted_amount = amount / exchange_rate
	
	return converted_amount, exchange_rate


@frappe.whitelist(allow_guest=True)
def create_mpesa_settings(**kwargs):
	"""Create Mpesa Settings for the team."""
	team = get_current_team()

	try:
		mpesa_settings = frappe.get_doc({
			"doctype": "Mpesa Settings",
			"team": team,  
			"payment_gateway_name": kwargs.get("payment_gateway_name"),
			"api_type": "Mpesa Express",
			"consumer_key": kwargs.get("consumer_key"),  
			"consumer_secret": kwargs.get("consumer_secret"),  
			"business_shortcode": kwargs.get("short_code"),  
			"till_number": kwargs.get("till_number"), 
			"online_passkey": kwargs.get("pass_key"), 
			"security_credential": kwargs.get("security_credential"),
			"sandbox": 1 if kwargs.get("sandbox") else 0,
		})

		mpesa_settings.insert(ignore_permissions=True)
		frappe.db.commit()

		return mpesa_settings.name 
	except Exception as e:
		frappe.log_error(message=f"Error creating Mpesa Settings: {str(e)}", title="M-Pesa Settings Creation Error")
		return None  


@frappe.whitelist(allow_guest=True)
def create_invoice_partner_site(data, gateway_controller):
	gateway=frappe.get_doc("Payment Gateway", gateway_controller)
	api_url_ = gateway.url
	api_key = gateway.api_key
	api_secret = get_decrypted_password("Payment Gateway", gateway.name, fieldname="api_secret")
	
	transaction_id = data.get("transaction_id")
	trans_amount = data.get("trans_amount")
	team = data.get("team")
	default_currency = data.get("default_currency")
	
	# Validate the necessary fields
	if not transaction_id or not trans_amount:
		frappe.throw(_("Invalid transaction data received"))

	api_url = api_url_

	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
	}
	# Define the payload to send with the POST request
	payload = {
		"transaction_id": transaction_id,
		"trans_amount": trans_amount,
		"team": team,
		"default_currency": default_currency
	}
	# Make the POST request to your API
	try:
		response = requests.post(api_url, data=payload, headers=headers)
		if response.status_code == 200:
			frappe.msgprint(_("Invoice created successfully"))
			response_data = response.json()
			download_link = response_data.get("message", "")
			return download_link
		else:
			frappe.log_error(f"API Error: {response.status_code} - {response.text}")
			frappe.throw(_("Failed to create the invoice via API"))

	except requests.exceptions.RequestException as e:
		frappe.log_error(f"Error calling API: {e}")
		frappe.throw(_("There was an issue connecting to the API."))


def update_tax_id(team, tax_id):
	"""Update the tax ID for the team."""
	doc_name=frappe.get_value("Team", {"user": team}, "name")
	team_doc = frappe.get_doc("Team", doc_name)
	if not team_doc.tax_id:
		team_doc.tax_id = tax_id
		team_doc.save()
  
@frappe.whitelist(allow_guest=True)
def get_tax_id():
	"""Get the tax ID for the team."""
	team=get_current_team()
	team_doc = frappe.get_doc("Team", team)
	return team_doc.tax_id if team_doc.tax_id else ''

@frappe.whitelist(allow_guest=True)
def display_invoices_by_partner():
	"""Display the list of invoices by partner."""
	team = get_current_team()
	invoices = frappe.get_all("Mpesa Payment Record", filters={"team":team}, fields=["name","posting_date", "trans_amount", "default_currency","local_invoice"])
	return invoices

@frappe.whitelist(allow_guest=True)
def get_exchange_rate(from_currency, to_currency):
	"""Get the latest exchange rate for the given currencies."""
	exchange_rate = frappe.db.get_value(
		"Currency Exchange",
		{"from_currency": from_currency, "to_currency": to_currency},
		"exchange_rate",
		order_by="creation DESC"  
	)
	return exchange_rate


@frappe.whitelist(allow_guest=True)
def create_payment_gateway_settings(**kwargs):
	"""Create Payment Gateway Settings for the team."""
	team = get_current_team() 
	args = frappe._dict(kwargs)

	try:

		payment_gateway_settings = frappe.get_doc({
			"doctype": "Payment Gateway",
			"team": team,
			"gateway": args.get("gateway_name"),
			"currency": args.get("currency"),
			"gateway_settings": args.get("gateway_setting"),
			"gateway_controller": args.get("gateway_controller"),
			"url": args.get("url"),
			"api_key": args.get("api_key"),
			"api_secret": args.get("api_secret"),
			"taxes_and_charges": args.get("taxes_and_charges"),
		})

		payment_gateway_settings.insert(ignore_permissions=True)
		frappe.db.commit()

		return payment_gateway_settings.name
	except Exception as e:
		print(str(e))
		frappe.log_error(message=f"Error creating Payment Gateway Settings: {str(e)}", title="Payment Gateway Settings Creation Error")
		return None

@frappe.whitelist(allow_guest=True)
def get_currency_options():
	"""Get the list of currencies supported by the system."""
	currencies=frappe.get_all("Currency", fields=["name"])
	names=[currency['name'] for currency in currencies]
	return names

@frappe.whitelist(allow_guest=True)
def get_gateway_settings():
	"""Get the list of doctypes supported by the system."""
	doctypes=frappe.get_all("DocType", fields=["name"])
	names=[doc['name'] for doc in doctypes]
	return names

@frappe.whitelist(allow_guest=True)
def get_gateway_controllers(gateway_setting):
	"""Get the list of controllers for the given doctype."""
	controllers = frappe.get_all(gateway_setting, fields=["name"])
	
	names = [doc['name'] for doc in controllers]
	
	return names 
