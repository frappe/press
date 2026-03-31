# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import os

import frappe

from press.api import account as account_api
from press.api import billing as billing_api
from press.saas.api import whitelist_saas_api


@whitelist_saas_api
def country_list():
	return account_api.country_list()


# Billing Information Related APIs
@whitelist_saas_api
def get_information(timezone=None):
	return account_api.get_billing_information(timezone)


@whitelist_saas_api
def update_information(billing_details: dict):
	team = frappe.local.get_team()
	team.update_billing_details(frappe._dict(billing_details))


@whitelist_saas_api
def validate_gst(address: dict):
	return billing_api.validate_gst(address)


@whitelist_saas_api
def change_payment_mode(mode: str):
	return billing_api.change_payment_mode(mode)


# Stripe Payment Gateway Related APIs
@whitelist_saas_api
def get_publishable_key_and_setup_intent():
	return billing_api.get_publishable_key_and_setup_intent()


@whitelist_saas_api
def setup_intent_success(setup_intent, address=None):
	return billing_api.setup_intent_success(setup_intent, address)


@whitelist_saas_api
def create_payment_intent_for_micro_debit(payment_method_name):
	return billing_api.create_payment_intent_for_micro_debit(payment_method_name)


@whitelist_saas_api
def create_payment_intent_for_buying_credits(amount):
	return billing_api.create_payment_intent_for_buying_credits(amount)


# Razorpay Payment Gateway Related APIs
@whitelist_saas_api
def create_razorpay_order(amount, type, doc_name=None):
	return billing_api.create_razorpay_order(amount, type, doc_name=doc_name)


@whitelist_saas_api
def handle_razorpay_payment_failed():
	return billing_api.handle_razorpay_payment_failed()


# Invoice Related APIs
@whitelist_saas_api
def get_invoices():
	return frappe.get_list(
		"Invoice",
		fields=[
			"name",
			"type",
			"invoice_pdf",
			"payment_mode",
			"stripe_invoice_id",
			"stripe_invoice_url",
			"due_date",
			"period_start",
			"period_end",
			"status",
			"total",
			"amount_paid",
			"amount_due",
			"stripe_payment_failed",
		],
		filters={"team": frappe.local.team_name},
		order_by="due_date desc, creation desc",
	)


@whitelist_saas_api
def upcoming_invoice():
	return billing_api.upcoming_invoice()


@whitelist_saas_api
def get_unpaid_invoices():
	invoices = billing_api.unpaid_invoices()
	unpaid_invoices = [invoice for invoice in invoices if invoice.status == "Unpaid"]
	if len(unpaid_invoices) == 1:
		return get_invoice(unpaid_invoices[0].name)
	return unpaid_invoices


@whitelist_saas_api
def total_unpaid_amount():
	return billing_api.total_unpaid_amount()


@whitelist_saas_api
def get_invoice(name: str):
	invoice = frappe.get_doc("Invoice", name)
	invoice.has_permission("read")
	data = invoice.as_dict()
	invoice.get_doc(data)
	return data


@whitelist_saas_api
def download_invoice(name: str):
	invoice = frappe.get_doc("Invoice", name)
	invoice.has_permission("read")
	if not invoice.invoice_pdf:
		frappe.throw("Invoice PDF not found")
	file_name = os.path.basename(invoice.invoice_pdf)
	file = frappe.get_doc("File", {"file_name": file_name})
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"


@whitelist_saas_api
def get_stripe_payment_url_for_invoice(name: str) -> str | None:
	try:
		invoice = frappe.get_doc("Invoice", name)
		if invoice.stripe_invoice_url:
			return invoice.stripe_invoice_url
		return invoice.get_stripe_payment_url()
	except frappe.DoesNotExistError:
		frappe.throw("Invoice not found")


# Payment Method Related APIs
@whitelist_saas_api
def get_payment_methods():
	return billing_api.get_payment_methods()


@whitelist_saas_api
def set_as_default(name):
	return billing_api.set_as_default(name)


@whitelist_saas_api
def remove_payment_method(name):
	return billing_api.remove_payment_method(name)
