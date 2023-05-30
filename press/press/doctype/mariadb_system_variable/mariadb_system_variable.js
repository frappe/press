// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB System Variable', {
	refresh(frm) {
		frm.add_web_link(
			`https://mariadb.com/kb/en/innodb-system-variables/#${frm.doc.name}`,
			__('Check MariaDB Documentation')
		);
	},
});
