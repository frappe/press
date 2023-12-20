// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Optimize Database Query', {
	add_suggested_index: (frm) => {
		return frappe.xcall(
			'press.press.doctype.optimize_database_query.optimize_database_query.add_suggested_index',
			{ name: frm.doc.site, optimizer: frm.doc.name },
		);
	},
});
