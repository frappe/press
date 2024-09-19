// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Press Webhook', {
	refresh(frm) {
		frm.add_custom_button(__('Activate'), () => {
			frm.call('activate').then((r) => {
				if (r.message) {
					frappe.msgprint(r.message);
				}
			});
		});
	},
});
