// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Staging Environment', {
	refresh(frm) {
		frm.add_custom_button(
			__('Create Release Group'),
			() => {
				frm.call('create_release_group').then(() => {
					frm.reload();
				});
			},
			__('Actions'),
		);
	},
});
