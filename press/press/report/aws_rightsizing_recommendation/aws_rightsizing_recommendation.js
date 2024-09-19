// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['AWS Rightsizing Recommendation'] = {
	onload: function (report) {
		report.page.add_button(__('Rightsize'), () => {
			frappe
				.call(
					'press.press.report.aws_rightsizing_recommendation.aws_rightsizing_recommendation.rightsize',
					{
						filters: {
							resource_type:
								frappe.query_report.get_filter_value('resource_type'),
							action_type: frappe.query_report.get_filter_value('action_type'),
						},
					},
				)
				.then((r) => {
					frappe.query_report.refresh();
				});
		});
	},
};
