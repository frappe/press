// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Devbox', {
	refresh(frm) {
		frm.add_custom_button(
			__('Get Available CPU and RAM'),
			() => {
				frm.call('get_available_cpu_and_ram');
			},
			__('Information'),
		);

		frm.add_custom_button(
			__('Pull Latest Image'),
			() => {
				frm.call('pull_latest_image');
			},
			__('Container'),
		);
	},
});
