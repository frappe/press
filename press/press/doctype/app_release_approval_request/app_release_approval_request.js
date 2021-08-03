// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release Approval Request', {
	refresh(frm) {
		if (frm.doc.status != 'Approved') {
			frm.add_custom_button('Approve Request', () => {
				frm.set_value('status', 'Approved');
				frm.save();
			});
		}
	},
	status(frm) {
		frm.set_value('approved_by', frappe.session.user);
	},
});
