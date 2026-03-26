// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident Investigator', {
	refresh(frm) {
		if (frm.doc.status == 'Pending' || frm.doc.status == 'Completed') {
			frm.add_custom_button(
				'Start Investigation',
				() => {
					frm.call('start_investigation').then(() => {
						frappe.msgprint({
							title: __('Start investigation'),
							indicator: 'green',
							message: __('Investigation started'),
						});
						frm.refresh();
					});
				},
				__('Actions'),
			);
		}
	},
});
