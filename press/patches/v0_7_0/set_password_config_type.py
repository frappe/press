# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	secret_keys = frappe.get_all(
		"Site Config Key", filters={"type": "Password"}, pluck="key"
	)

	site_config_keys_that_should_be_secret = frappe.get_all(
		"Site Config", filters={"key": ("in", secret_keys)}, pluck="name"
	)

	for key in site_config_keys_that_should_be_secret:
		frappe.db.set_value("Site Config", key, "type", "Password")

	common_site_config_keys_that_should_be_secret = frappe.get_all(
		"Common Site Config", filters={"key": ("in", secret_keys)}, pluck="name"
	)

	for key in common_site_config_keys_that_should_be_secret:
		frappe.db.set_value("Common Site Config", key, "type", "Password")
