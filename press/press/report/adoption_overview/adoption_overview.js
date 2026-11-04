// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Adoption Overview'] = {
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
			fieldname: 'release_group',
			label: __('Release Group'),
			fieldtype: 'Link',
			options: 'Release Group',
			description: __(
				'Shows the hourly rows of a signup, public or central group. Leave empty for the fleet by group type.',
			),
		},
	],
}
