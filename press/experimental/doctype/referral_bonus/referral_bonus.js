// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Referral Bonus', {
	refresh: function (frm) {
		if (!frm.doc.credits_allocated) {
			frm.add_custom_button('Allocate Credits', () => {
				frm.call('allocate_credits').then(() => {
					frm.refresh();
				});
			});
		}
	},
});
