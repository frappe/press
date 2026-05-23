# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from tqdm import tqdm


def execute():
	exchange_rate = frappe.db.get_single_value("Press Settings", "usd_rate")
	payout_orders = frappe.get_all(
		"Payout Order",
		{"docstatus": 0},
		["name", "net_total_dzd", "net_total_usd", "recipient_currency"],
	)

	for payout_order in tqdm(payout_orders):
		total_amount = 0
		if payout_order.recipient_currency == "USD":
			dzd_in_usd = 0
			if payout_order.net_total_dzd > 0:
				dzd_in_usd = payout_order.net_total_dzd / exchange_rate
			total_amount = payout_order.net_total_usd + dzd_in_usd
		elif payout_order.recipient_currency == "DZD":
			total_amount = (
				payout_order.net_total_dzd + payout_order.net_total_usd * exchange_rate
			)

		frappe.db.set_value("Payout Order", payout_order.name, "total_amount", total_amount)
