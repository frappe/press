# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.geo.country_info import get_country_timezone_info

from press.api.account import get_account_request_from_key


@frappe.whitelist(allow_guest=True)
def options_for_regional_data(key: str):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	data = {
		"languages": frappe.db.get_all("Language", ["language_name", "language_code"]),
		"currencies": frappe.db.get_all("Currency", pluck="name"),
		"country": account_request.country,
	}
	data.update(get_country_timezone_info())

	return data
