// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['MariaDB Locks List'] = {
	after_refresh(report) {
		let should_poll = report.get_filter_value('poll');
		if (!should_poll || report.polling_interval) return;

		frappe.toast(
			'This report will be auto-refreshed every 5 seconds till we find a lock wait.',
		);

		report.polling_interval = setInterval(() => {
			if (!report.data.length) {
				report.refresh();
			} else {
				clearInterval(report.polling_interval);
			}
		}, 5000);
	},
};
