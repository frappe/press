// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Press Settings', {
	refresh: function(frm) {
		frm.add_custom_button(
			__('Obtain TLS Certificate'),
			() => {
				frm.call({
					method: 'obtain_root_domain_tls_certificate',
					doc: frm.doc,
					callback: () => frappe.refresh()
				});
			},
			__('TLS')
		);
	},
	create_stripe_webhook(frm) {
		frm.call('create_stripe_webhook');
	}
});
