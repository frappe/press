// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server Firewall', {
	refresh(frm) {
		[['Sync', 'sync']].forEach(([label, action]) => {
			frm.add_custom_button(__(label), () => {
				frm.call(action).then(() => {
					frm.refresh();
				});
			});
		});
	},
});
