// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['MariaDB Deadlock Browser'] = {
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
			reqd: 1,
		},
		{
			fieldname: 'stop_datetime',
			label: __('End At'),
			fieldtype: 'Datetime',
			reqd: 1,
		},
		{
			fieldname: 'max_lines',
			label: __('Max Lines'),
			fieldtype: 'Int',
			default: 4000,
		},
	],
};
