// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Payment Webhook Delays'] = {
	filters: [
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
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
			fieldname: 'gateway',
			label: __('Gateway'),
			fieldtype: 'Select',
			options: ['', 'Razorpay', 'Stripe'],
		},
		{
			fieldname: 'only_delayed',
			label: __('Only Delayed or Failed'),
			fieldtype: 'Check',
			default: 1,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)
		if (column.fieldname === 'status' && data?.status === 'Failed') {
			return `<span style="color: var(--red-600)">${value}</span>`
		}
		if (column.fieldname === 'delivery_delay' && data?.delivery_delay > 60) {
			return `<span style="color: var(--orange-600)">${value}</span>`
		}
		return value
	},
}
