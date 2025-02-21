// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Domain', {
	refresh: function (frm) {
		frm.add_custom_button('Create DNS Record', () => {
			frm.call('create_dns_record').then((r) => frm.refresh());
		});
	},
});
