// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Product Usage'] = {
	filters: [
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			reqd: 1,
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: 'product_apps_only',
			label: __('Product Trial Apps Only'),
			fieldtype: 'Check',
			default: 1,
			description: __(
				'Shows only the apps of Product Trials. Clear it to show every installed app.',
			),
		},
	],
}
