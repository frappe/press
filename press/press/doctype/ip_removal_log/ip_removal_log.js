// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('IP Removal Log', {
	refresh(frm) {
		if (frm.doc.status === 'Pending') {
			frm.add_custom_button(
				__('Start'),
				() => {
					frm.call('execute_removal_steps').then((r) => {
						if (!r.exc) {
							frappe.show_alert('Queued IP Removal Steps for Execution');
							frm.refresh();
						}
					});
				},
				__('Actions'),
			);
		}
	},
});
