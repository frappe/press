# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import stripe
from datetime import datetime
from frappe.utils import global_date_format, fmt_money
from press.utils import get_current_team


@frappe.whitelist()
def get_publishable_key_and_setup_intent():
	team = get_current_team()
	return {
		"publishable_key": get_publishable_key(),
		"setup_intent": get_setup_intent(team),
	}


@frappe.whitelist()
def get_invoices():
	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)
	has_subscription = team_doc.has_subscription()
	if not has_subscription:
		return

	invoice = team_doc.get_upcoming_invoice()
	customer_name = invoice["customer_name"]
	customer_email = invoice["customer_email"]
	next_payment_attempt = invoice["next_payment_attempt"]
	total_amount = invoice["total"]
	currency = team_doc.transaction_currency
	past_payments = team_doc.get_past_payments()
	upcoming_invoice = {
		"next_payment_attempt": global_date_format(
			datetime.fromtimestamp(next_payment_attempt)
		),
		"amount": format_stripe_money(total_amount, currency),
		"customer_email": customer_email,
	}

	return {
		"upcoming_invoice": upcoming_invoice,
		"past_payments": past_payments,
	}


def format_stripe_money(amount, currency):
	return fmt_money(amount / 100, 2, currency)


@frappe.whitelist()
def get_payment_methods():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_payment_methods()


@frappe.whitelist()
def after_card_add():
	clear_setup_intent()
	set_currency_and_default_payment_method()
	create_subscription()


def clear_setup_intent():
	team = get_current_team()
	frappe.cache().hdel("setup_intent", team)


def set_currency_and_default_payment_method():
	team = get_current_team()
	frappe.get_doc("Team", team).set_currency_and_default_payment_method()


def create_subscription():
	team = get_current_team()
	doc = frappe.get_doc({"doctype": "Subscription", "team": team, "status": "Active"})
	doc.insert(ignore_permissions=True)


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
