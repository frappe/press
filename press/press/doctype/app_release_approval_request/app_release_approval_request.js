// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release Approval Request', {
	refresh(frm) {
		if (['Open', 'Rejected'].includes(frm.doc.status)) {
			frm.add_custom_button('Approve Request', () => {
				frm.set_value('status', 'Approved');
				frm.save();
			});
		}
	},
	status(frm) {
		frm.set_value('reviewed_by', frappe.session.user);
	},
});
