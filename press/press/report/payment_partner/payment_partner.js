// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Payment Partner'] = {
	filters: [
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: 'team',
			label: __('Team'),
			fieldtype: 'Link',
			options: 'Team',
		},

		{
			fieldname: 'payment_partner',
			label: __('Payment Partner'),
			fieldtype: 'Link',
			options: 'Team',
		},
		{
			fieldname: 'payment_gateway',
			label: __('Payment Gateway'),
			fieldtype: 'Link',
			options: 'Payment Gateway',
		},
		{
			fieldname: 'submitted_to_frappe',
			label: __('Submitted to Frappe'),
			fieldtype: 'Check',
		},
	],
};
