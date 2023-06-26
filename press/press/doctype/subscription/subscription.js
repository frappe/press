// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription', {
	refresh: function (frm) {
		frm.add_custom_button('Create Usage Record', () =>
			frm.call('create_usage_record')
		);
	},
});
