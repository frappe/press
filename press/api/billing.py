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
from press.press.doctype.mpesa_setup.mpesa_connector import MpesaConnector
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
from press.utils.mpesa_utils import create_mpesa_request_log

# from press.press.doctype.paymob_callback_log.paymob_callback_log import create_payment_partner_transaction


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
	return team.get_past_invoices()


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


def get_processed_balance_transactions(transactions: list[dict]):
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


def get_cleaned_up_transactions(transactions: list[dict]):
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
def fetch_invoice_items(invoice):
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
def get_customer_details(team):
	"""This method is called by frappe.io for creating Customer and Address"""
	team_doc = frappe.db.get_value("Team", team, "*")
	return {
		"team": team_doc,
		"address": frappe.get_doc("Address", team_doc.billing_address),
	}


@frappe.whitelist()
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
def get_payment_methods():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_payment_methods()


@frappe.whitelist()
def set_as_default(name):
	payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": get_current_team()})
	payment_method.set_default()


@frappe.whitelist()
def remove_payment_method(name):
	team = get_current_team()
	payment_method_count = frappe.db.count("Stripe Payment Method", {"team": team})

	if has_unsettled_invoices(team) and payment_method_count == 1:
		return "Unpaid Invoices"

	payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": team})
	payment_method.delete()
	return None


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
		verified_with_micro_charge=True,
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
			frappe.throw("Invalid GSTIN. The input you've entered does not match the format of GSTIN.")

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
		if unpaid_invoice.payment_mode == "Prepaid Credits" and team_has_balance_for_invoice(unpaid_invoice):
			return None

		return unpaid_invoice
	return None


def team_has_balance_for_invoice(prepaid_mode_invoice):
	team = get_current_team(get_doc=True)
	return team.get_balance() >= prepaid_mode_invoice.amount_due


@frappe.whitelist()
def create_razorpay_order(amount, type=None):
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
	if type and type == "Partnership Fee":
		data.get("notes").update({"Type": type})
	order = client.order.create(data=data)

	payment_record = frappe.get_doc(
		{"doctype": "Razorpay Payment Record", "order_id": order.get("id"), "team": team.name, "type": type}
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
			{"status": "Unpaid", "team": team.name, "type": "Subscription", "docstatus": ("!=", 2)},
			["sum(amount_due) as total"],
			pluck="total",
		)[0]
		or 0
	) + negative_balance


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
			status = "Failed"
			create_mpesa_request_log(
				transaction_response, "Host", "Mpesa Express", integration_request, None, status
			)
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
		"default_currency": "KES",
		"rate": info.requested_amount,
	}
	mpesa_invoice, invoice_name = create_invoice_partner_site(data, gateway_name)
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


def parse_datetime(date):
	from datetime import datetime

	return datetime.strptime(str(date), "%Y%m%d%H%M%S")
