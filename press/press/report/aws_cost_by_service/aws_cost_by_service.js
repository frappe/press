// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['AWS Cost By Service'] = {
	filters: [
		{
			fieldname: 'lookback_months',
			label: __('Lookback Period'),
			fieldtype: 'Select',
			options: '3\n6\n12',
			default: '6',
		},
		{
			fieldname: 'service',
			label: __('Service'),
			fieldtype: 'Data',
		},
	],
}
