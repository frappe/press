// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['AWS VM Cost Utilization'] = {
	filters: [
		{
			fieldname: 'cluster',
			label: __('Cluster'),
			fieldtype: 'Link',
			options: 'Cluster',
			get_query: function () {
				return {
					filters: { cloud_provider: 'AWS EC2' },
				}
			},
		},
		{
			fieldname: 'aws_status',
			label: __('AWS Status'),
			fieldtype: 'Select',
			options: '\npending\nrunning\nstopping\nstopped\nshutting-down',
		},
	],
}
