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
	},
});
