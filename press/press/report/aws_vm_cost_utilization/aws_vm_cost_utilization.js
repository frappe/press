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
	onload: function (report) {
		report.page.add_inner_message(
			__(
				'Instances are read live from AWS (not from cached Press status). "Tracked In Press" is unchecked when AWS is billing for an instance with no matching Virtual Machine record in Press. Cost is an on-demand list-price estimate for running instances (compute only); it excludes EBS storage and any Reserved Instance / Savings Plan discounts.',
			),
		)
	},
}
