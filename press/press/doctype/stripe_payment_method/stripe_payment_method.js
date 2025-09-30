// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stripe Payment Method', {
	refresh: function (frm) {
		frappe.dynamic_link = {
			doc: frm.doc,
			fieldname: 'name',
			doctype: 'Stripe Payment Method',
		};
		frappe.contacts.render_address_and_contact(frm);

		if (frm.doc.stripe_mandate_id) {
			frm.add_custom_button('Check Mandate Status', () => {
				frm.call('check_mandate_status').then((r) => {
					if (r.message) {
						frappe.msgprint(`Mandate status: ${r.message}`);
					} else {
						frappe.msgprint('No mandate found or status is not available.');
					}
				});
			});
		}
	},
});
