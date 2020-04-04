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
	create_stripe_plans(frm) {
		if (frm.doc.stripe_product_id) {
			frappe.confirm(
				// prettier-ignore
				__('This will create new Stripe Plans. If there are existing customers who were on old plans, they will have to be migrated over. Are you sure you want to continue?'),
				() => {
					call_method();
				}
			);
		} else {
			call_method();
		}

		function call_method() {
			frm.call('create_stripe_plans');
		}
	},
	create_stripe_webhook(frm) {
		frm.call('create_stripe_webhook');
	}
});
