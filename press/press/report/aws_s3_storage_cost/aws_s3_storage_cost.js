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
	onload: function (report) {
		report.page.add_inner_message(
			__(
				'Growth figures reflect net bucket-size change (CloudWatch BucketSizeBytes), not gross bytes uploaded. Storage cost is an S3 Standard-tier approximation — buckets on Infrequent Access/Glacier tiers are not priced accurately here.',
			),
		)
	},
}
