# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api


@whitelist_saas_api
def info():
	team = frappe.local.get_team()
	billing_address_added = bool(team.billing_address)
	payment_mode_added = bool(team.payment_mode)
	billing_address = (
		frappe.get_doc("Address", team.billing_address).as_dict()
		if billing_address_added
		else None
	)
	if billing_address:
		billing_address.billing_name = team.billing_name
	return {
		"billing_address_added": billing_address_added,
		"payment_mode_added": payment_mode_added,
		"billing_address": billing_address,
		"payment_mode": team.payment_mode or "",
		"balance": team.get_balance(),
		"default_payment_method": frappe.db.get_value(
			"Stripe Payment Method",
			{"team": team.name, "name": team.default_payment_method},
			[
				"name",
				"last_4",
				"name_on_card",
				"expiry_month",
				"expiry_year",
				"brand",
			],
			as_dict=True,
		),
	}


@whitelist_saas_api
def update_address():
	pass


@whitelist_saas_api
def update_payment_mode():
	pass
