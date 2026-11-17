// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Update Laggards'] = {
	filters: [
		{
			fieldname: 'group_type',
			label: __('Group Type'),
			fieldtype: 'Select',
			options: '\nSignup\nCentral\nPublic\nPrivate',
		},
		{
			fieldname: 'release_group',
			label: __('Release Group'),
			fieldtype: 'Link',
			options: 'Release Group',
		},
		{
			fieldname: 'server',
			label: __('Server'),
			fieldtype: 'Link',
			options: 'Server',
		},
		{
			fieldname: 'reason',
			label: __('Reason'),
			fieldtype: 'Select',
			options:
				'\nFatal Update\nFailed Update\nUpdating\nMissing App\nEarlier Failure\nAuto Updates Off\nOwn Update Schedule\nWaiting',
		},
	],
}
