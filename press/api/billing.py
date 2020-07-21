# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import stripe
from datetime import datetime
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

	if invoice:
		customer_email = invoice.customer_email
		total_amount = invoice.amount_due
		currency = team_doc.currency
		next_payment_attempt = (
			global_date_format(invoice.due_date) if invoice.due_date else None
		)
		upcoming_invoice = {
			"next_payment_attempt": next_payment_attempt,
			"amount": invoice.get_formatted('amount_due'),
			"total_amount": invoice.get_formatted('total'),
			"customer_email": invoice.customer_email,
		}
	else:
		upcoming_invoice = None

	past_payments = team_doc.get_past_payments()

	return {
		"upcoming_invoice": upcoming_invoice,
		"past_payments": past_payments,
		"payment_method": team_doc.default_payment_method,
		"available_credits": fmt_money(team_doc.get_available_credits(), 2, currency),
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
		"Transferred Credits from ERPNext Cloud. Transaction ID: {0}".format(transaction_id),
	)


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
def get_payment_methods():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_payment_methods()


@frappe.whitelist()
def after_card_add():
	clear_setup_intent()


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
