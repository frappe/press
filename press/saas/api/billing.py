# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api
from press.api import billing as billing_api
from press.api import account as account_api


@whitelist_saas_api
def country_list():
	return account_api.country_list()

@whitelist_saas_api
def get_information(timezone=None):
	return account_api.get_billing_information(timezone)


@whitelist_saas_api
def update_information(billing_details:dict):
	team = frappe.local.get_team()
	team.update_billing_details(frappe._dict(billing_details))


@whitelist_saas_api
def validate_gst(address:dict):
	return billing_api.validate_gst(address)

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
