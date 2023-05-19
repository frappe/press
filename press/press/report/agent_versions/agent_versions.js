// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Agent Versions'] = {
	onload: function (report) {
		report.page.add_button(__('Update Agent'), () => {
			frappe
				.call('press.press.report.agent_versions.agent_versions.update_agent', {
					filters: {
						team: frappe.query_report.get_filter_value('team'),
						server_type: frappe.query_report.get_filter_value('server_type'),
						exclude_self_hosted: frappe.query_report.get_filter_value(
							'exclude_self_hosted'
						),
					},
				})
				.then((r) => {
					frappe.query_report.refresh();
				});
		});
	},
};
