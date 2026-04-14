// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB Upgrade', {
	refresh(frm) {
		if (frm.doc.status !== 'Pending') {
			return;
		}
		frm
			.add_custom_button('Start Upgrade', () => {
				frm.call('start').then(() => {
					frappe.msgprint(
						'MariaDB Upgrade has been started. Please check the workflow for progress.',
					);
				});
			})
			.addClass('btn-primary');
	},
});
