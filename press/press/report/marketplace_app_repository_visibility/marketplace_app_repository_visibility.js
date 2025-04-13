// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Marketplace App Repository Visibility'] = {
	filters: [],
	onload: async function (report) {
		report.page.add_inner_button(__('Send Email to Developers'), () => {
			frappe.confirm('Are you sure you want to send out the e-mails?', () => {
				frappe.xcall(
					'press.press.report.marketplace_app_repository_visibility.marketplace_app_repository_visibility.send_emails',
					{
						columns: JSON.stringify(report.columns),
						data: JSON.stringify(report.data),
					},
				);
			});
		});
	},
};
