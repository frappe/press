// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['AWS S3 Storage Cost'] = {
	filters: [
		{
			fieldname: 'bucket',
			label: __('Bucket'),
			fieldtype: 'Data',
		},
	],
}
