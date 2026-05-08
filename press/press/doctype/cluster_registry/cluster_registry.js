// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cluster Registry', {
	refresh(frm) {
		frm.add_custom_button(
			__('Setup Project'),
			function () {
				frm.call('setup_project').then((r) => frm.refresh());
			},
			__('Actions'),
		);

		frm.add_web_link(
			`https://${frm.doc.name}/harbor/projects`,
			__('Visit Harbor Dashboard'),
		);
	},
});
