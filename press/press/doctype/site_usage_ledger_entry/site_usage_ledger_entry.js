// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Usage Ledger Entry', {
	refresh: function(frm) {
		if (!frm.doc.stripe_usage_record_id) {
			frm.add_custom_button(__('Create Usage Record on Stripe'), () => {
				frm.call('create_usage_record_on_stripe').then(() => frm.refresh());
			});
		}
	}
});
