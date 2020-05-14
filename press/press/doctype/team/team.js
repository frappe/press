// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Team', {
	refresh: function (frm) {
		frm.add_custom_button(
			'Sites',
			() => frappe.set_route('List', 'Site', { team: frm.doc.name }),
			'View'
		);
		frm.add_custom_button(
			'Payments',
			() => frappe.set_route('List', 'Payment', { team: frm.doc.name }),
			'View'
		);
		frm.add_custom_button(
			'Payment Ledger Entries',
			() => frappe.set_route('List', 'Payment Ledger Entry', { team: frm.doc.name }),
			'View'
		);
	},
});
