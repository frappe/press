# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import re
import frappe
import stripe
from frappe.utils import global_date_format, fmt_money, flt
from press.utils import get_current_team


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
		next_payment_attempt = (
			global_date_format(invoice.due_date) if invoice.due_date else None
		)
		upcoming_invoice = {
			"next_payment_attempt": next_payment_attempt,
			"amount": invoice.get_formatted("amount_due"),
			"total_amount": invoice.get_formatted("total"),
			"customer_email": invoice.customer_email,
		}
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


def format_stripe_money(amount, currency):
	return fmt_money(amount / 100, 2, currency)


def get_erpnext_com_connection():
	from frappe.frappeclient import FrappeClient

	# TODO: Remove password authentication when API Key Authentication bug is fixed
	press_settings = frappe.get_single("Press Settings")
	erpnext_password = frappe.utils.password.get_decrypted_password(
		"Press Settings", "Press Settings", fieldname="erpnext_password"
	)
	return FrappeClient(
		press_settings.erpnext_url,
		username=press_settings.erpnext_username,
		password=erpnext_password,
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
		amount=amount * 100, currency=team.currency.lower(), customer=team.stripe_customer_id
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

	usage = []
	for row in doc.items:
		usage.append(
			{
				"idx": row.idx,
				"site": row.document_name,
				"plan": frappe.get_cached_value("Plan", row.plan, "plan_title") if row.plan else None,
				"days_active": row.quantity,
				"rate": row.get_formatted("rate"),
				"amount": row.get_formatted("amount"),
			}
		)

	return {
		"usage": usage,
		"status": doc.status,
		"invoice_pdf": doc.get_pdf() if doc.currency == "USD" else doc.invoice_pdf,
		"period_start": doc.period_start,
		"period_end": doc.period_end,
		"total": doc.get_formatted("total"),
		"amount_due": doc.get_formatted("amount_due"),
		"applied_balance": doc.get_formatted("applied_credits"),
	}


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
	team.create_or_update_address(address)
	team.update_onboarding("Add Billing Information", "Completed")


def clear_setup_intent():
	team = get_current_team()
	frappe.cache().hdel("setup_intent", team)


def get_publishable_key():
	strip_account = frappe.db.get_single_value("Press Settings", "stripe_account")
	return frappe.db.get_value("Stripe Settings", strip_account, "publishable_key")


def get_setup_intent(team):
	intent = frappe.cache().hget("setup_intent", team)
	if not intent:
		customer_id = frappe.db.get_value("Team", team, "stripe_customer_id")
		stripe = get_stripe()
		intent = stripe.SetupIntent.create(
			customer=customer_id, payment_method_types=["card"]
		)
		frappe.cache().hset("setup_intent", team, intent)
	return intent


def get_stripe():
	if not hasattr(frappe.local, "press_stripe_object"):
		stripe_account = frappe.db.get_single_value("Press Settings", "stripe_account")
		secret_key = frappe.utils.password.get_decrypted_password(
			"Stripe Settings", stripe_account, "secret_key"
		)
		stripe.api_key = secret_key
		frappe.local.press_stripe_object = stripe
	return frappe.local.press_stripe_object


states_with_tin = {
	"Andaman and Nicobar Islands": "35",
	"Andhra Pradesh": "37",
	"Arunachal Pradesh": "12",
	"Assam": "18",
	"Bihar": "10",
	"Chandigarh": "04",
	"Chattisgarh": "22",
	"Dadra and Nagar Haveli": "26",
	"Daman and Diu": "25",
	"Delhi": "07",
	"Goa": "30",
	"Gujarat": "24",
	"Haryana": "06",
	"Himachal Pradesh": "02",
	"Jammu and Kashmir": "01",
	"Jharkhand": "20",
	"Karnataka": "29",
	"Kerala": "32",
	"Ladakh": "38",
	"Lakshadweep Islands": "31",
	"Madhya Pradesh": "23",
	"Maharashtra": "27",
	"Manipur": "14",
	"Meghalaya": "17",
	"Mizoram": "15",
	"Nagaland": "13",
	"Odisha": "21",
	"Other Territory": "97",
	"Pondicherry": "34",
	"Punjab": "03",
	"Rajasthan": "08",
	"Sikkim": "11",
	"Tamil Nadu": "33",
	"Telangana": "36",
	"Tripura": "16",
	"Uttar Pradesh": "09",
	"Uttarakhand": "05",
	"West Bengal": "19",
}


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
