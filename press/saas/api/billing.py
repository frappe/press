# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api
from press.api import billing as billing_api
from press.utils.country_timezone import get_country_from_timezone


@whitelist_saas_api
def info(timezone=None):
	team = frappe.local.get_team()
	billing_address_added = bool(team.billing_address)
	payment_mode_added = bool(team.payment_mode)
	billing_address = (
		frappe.get_doc("Address", team.billing_address).as_dict()
		if billing_address_added
		else frappe._dict()
	)
	billing_address.billing_name = team.billing_name
	if not billing_address.country and timezone:
		billing_address.country = get_country_from_timezone(timezone)
	micro_debit_charge_field = (
		"micro_debit_charge_usd" if team.currency == "USD" else "micro_debit_charge_inr"
	)
	return {
		"billing_address_added": billing_address_added,
		"payment_mode_added": payment_mode_added,
		"billing_address": billing_address,
		"currency": team.currency or "",
		"micro_debit_charge_amount": frappe.db.get_single_value(
			"Press Settings", micro_debit_charge_field
		),
		"payment_mode": team.payment_mode or "",
		"balance": team.get_balance(),
	}


@whitelist_saas_api
def update_address(billing_details):
	team = frappe.local.get_team()
	team.update_billing_details(billing_details)


@whitelist_saas_api
def get_publishable_key_and_setup_intent():
	return billing_api.get_publishable_key_and_setup_intent()


@whitelist_saas_api
def setup_intent_success(setup_intent, address=None):
	return billing_api.setup_intent_success(setup_intent, address)


@frappe.whitelist()
def create_payment_intent_for_micro_debit(payment_method_name):
	return billing_api.create_payment_intent_for_micro_debit(payment_method_name)


@whitelist_saas_api
def update_payment_mode():
	pass
