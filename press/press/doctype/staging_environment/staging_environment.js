// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Staging Environment', {
	refresh(frm) {
		frm.add_custom_button(
			__('Deploy Environment'),
			() => {
				frm.call('deploy').then(() => {
					frm.reload();
				});
			},
			__('Actions'),
		);
		frm.add_custom_button(
			__('Destroy Environment'),
			() => {
				frm.call('delete').then(() => {
					frm.reload();
				});
			},
			__('Actions'),
		);
	},
});
