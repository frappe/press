// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Org", {
	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Org' };
		frappe.contacts.render_address_and_contact(frm);
	},
});
