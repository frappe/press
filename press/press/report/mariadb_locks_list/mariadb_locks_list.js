// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['MariaDB Locks List'] = {
	after_datatable_render() {
		let should_poll = frappe.query_report.get_filter_value('poll');
		if (!should_poll) return;

		frappe.toast(
			'This report will be auto-refreshed every 5 seconds till we find a lock wait.',
		);

		frappe.query_report.polling_interval = setInterval(() => {
			if (!frappe.query_report.data.length) {
				frappe.query_report.refresh();
			} else {
				clearInterval(frappe.query_report.polling_interval);
			}
		}, 5000);
	},
};
