// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Auto Scale Record', {
	refresh(frm) {
		if (frm.doc.status === 'Failure') {
			frm.add_custom_button('Force Continue', () => {
				frm.call('force_continue').then((r) => {
					if (r.message) {
						frappe.msgprint(r.message);
					} else {
						frm.refresh();
					}
				});
			});
		}
	},
});
