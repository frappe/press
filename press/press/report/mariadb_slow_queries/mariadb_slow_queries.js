// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['MariaDB Slow Queries'] = {
	filters: [
		{
			fieldname: 'site',
			label: __('Site'),
			fieldtype: 'Link',
			options: 'Site',
			reqd: 1,
		},
		{
			fieldname: 'start_datetime',
			label: __('Start From'),
			fieldtype: 'Datetime',
			default: frappe.datetime.add_days(frappe.datetime.now_datetime(), -1),
			reqd: 1,
		},
		{
			fieldname: 'stop_datetime',
			label: __('End At'),
			fieldtype: 'Datetime',
			default: frappe.datetime.now_datetime(),
			reqd: 1,
		},
		{
			fieldname: 'normalize_queries',
			label: __('Normalize Queries'),
			fieldtype: 'Check',
		},
		{
			fieldname: 'analyze',
			label: __('Suggest Indexes'),
			fieldtype: 'Check',
			depends_on: 'eval: doc.normalize_queries',
		},
		{
			fieldname: 'max_lines',
			label: __('Max Lines'),
			default: 100,
			fieldtype: 'Int',
		},
		{
			fieldname: 'search_pattern',
			label: __('Search Pattern'),
			fieldtype: 'Data',
			default: '.*',
		},
	],
};
