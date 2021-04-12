// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Account Request', {
	refresh: function (frm) {
		frm.add_custom_button('Send verification email', () => {
			frm.call('send_verification_email');
		});
	},
});
