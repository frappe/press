# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import stripe


@frappe.whitelist()
def get_publishable_key_and_setup_intent():
	team = frappe.get_request_header("X-Press-Team")
	if not team:
		frappe.throw("Invalid Team")

	return {
		"publishable_key": get_publishable_key(),
		"setup_intent": get_setup_intent(team),
	}


@frappe.whitelist()
def get_payment_methods():
	team = frappe.get_request_header("X-Press-Team")
	customer_id = frappe.db.get_value("Team", team, "stripe_customer_id")
	stripe = get_stripe()
	res = stripe.PaymentMethod.list(customer=customer_id, type="card")
	return res["data"] or []


@frappe.whitelist()
def clear_setup_intent():
	team = frappe.get_request_header("X-Press-Team")
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
