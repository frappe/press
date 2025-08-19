// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Build Metric', {
	refresh(frm) {
		frm.add_custom_button(
			'Get Metrics',
			() => {
				frm.call('get_metrics').then(() => {
					frappe.msgprint({
						title: __('Get Metrics'),
						indicator: 'green',
						message: __('Getting metrics'),
					});
					frm.refresh();
				});
			},
			__('Actions'),
		);
	},
});
