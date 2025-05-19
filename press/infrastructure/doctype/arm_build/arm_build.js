// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('ARM Build', {
	refresh(frm) {
		[
			[__('Sync Status'), 'sync_status'],
			[__('Pull Images'), 'pull_images'],
		].forEach(([label, method, condition]) => {
			if (condition || typeof condition == 'undefined') {
				frm.add_custom_button(
					label,
					() => {
						frm.call(method);
					},
					__('Actions'),
				);
			}
		});
	},
});
