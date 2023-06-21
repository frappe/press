// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB Variable', {
	refresh(frm) {
		let root = 'https://mariadb.com/kb/en/';
		frm.add_web_link(
			`${root}${frm.doc.doc_section}-system-variables/#${frm.doc.name}`,
			__('Check MariaDB Documentation'),
		);
	},
});
