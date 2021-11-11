// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Referral Bonus', {
	refresh: function (frm) {
		if (!frm.doc.credits_allocated) {
			let btn = frm.add_custom_button('Allocate Credits', () => {
				frm
					.call({
						doc: frm.doc,
						method: 'allocate_credits',
						btn,
					})
					.then(() => {
						frm.refresh();
					});
			});
		}
	},
});
