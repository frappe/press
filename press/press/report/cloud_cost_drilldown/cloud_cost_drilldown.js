// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Cloud Cost Drilldown'] = {
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
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: 'group_by',
			label: __('Group By'),
			fieldtype: 'Select',
			options: 'Provider\nService\nUsage Type\nRegion\nDate',
			default: 'Service',
			reqd: 1,
		},
		{
			fieldname: 'currency',
			label: __('Currency'),
			fieldtype: 'Link',
			options: 'Currency',
			default: 'USD',
			reqd: 1,
			description: __(
				'Providers bill in different currencies and are never summed together',
			),
		},
		{
			fieldname: 'provider',
			label: __('Provider'),
			fieldtype: 'Select',
			options: '\nAWS EC2\nOCI\nHetzner\nDigitalOcean',
		},
		{
			fieldname: 'source',
			label: __('Source'),
			fieldtype: 'Select',
			options: '\nBilled\nAccrued',
			description: __(
				'Accrued is our own inventory priced at the provider rate card, not an invoice',
			),
		},
		{
			fieldname: 'service',
			label: __('Service'),
			fieldtype: 'Data',
			description: __(
				'Set this, then group by Usage Type to see what inside it moved',
			),
		},
		{
			fieldname: 'usage_type',
			label: __('Usage Type'),
			fieldtype: 'Data',
		},
		{
			fieldname: 'region',
			label: __('Region'),
			fieldtype: 'Data',
		},
		{
			fieldname: 'account',
			label: __('Account'),
			fieldtype: 'Data',
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)
		if (column.fieldname === 'change_percent' && data && data.change_percent) {
			const colour =
				data.change_percent > 0 ? 'var(--red-600)' : 'var(--green-600)'
			value = `<span style="color: ${colour}">${value}</span>`
		}
		return value
	},
}
