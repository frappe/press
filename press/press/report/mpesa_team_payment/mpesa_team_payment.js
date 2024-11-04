// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports["Mpesa Team Payment"] = {
	"filters": [
				{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
				}
				,
				{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
				}
				,
				{
			"fieldname":"team",
			"label": __("Team"),
			"fieldtype": "Link",
			"options": "Team",
				}
				,
			
				{
			"fieldname":"payment_partner",
			"label": __("Payment Partner"),
			"fieldtype": "Link",
			"options": "Team",
				},
				{
					"fieldname":"transaction_type",
					"label": __("Transaction Type"),
					"fieldtype": "Select",
					"options": "\nMpesa Express\nMpesa C2B",
					"default": "Mpesa Express",
						},
			
				

	]
};
