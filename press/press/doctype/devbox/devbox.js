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

		if (!frm.doc.initialized) {
			frm.add_custom_button(
				__('Initialize'),
				() => {
					frm.call('initialize_devbox');
				},
				__('Actions'),
			);
		}
	},
});
