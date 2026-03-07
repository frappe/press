// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server Firewall', {
	refresh(frm) {
		[
			['↑', 'Setup', 'setup'],
			['↓', 'Teardown', 'teardown'],
			['🗘', 'Sync', 'sync'],
		].forEach(([icon, label, action]) => {
			frm.add_custom_button(icon + ' ' + __(label), () => {
				frm.call(action).then(() => {
					frm.refresh();
				});
			});
		});
	},
});
