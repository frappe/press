// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Source', {
	refresh: function (frm) {
		[[__('Create App Release'), 'create_release']].forEach(
			([label, method]) => {
				frm.add_custom_button(
					label,
					() => {
						frm.call(method).then((r) => frm.refresh());
					},
					__('Actions'),
				);
			},
		);
	},
});
