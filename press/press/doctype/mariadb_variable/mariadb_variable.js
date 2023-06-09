// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB Variable', {
	refresh(frm) {
		let root = 'https://mariadb.com/kb/en/';
		let prefix = 'innodb-';
		if (frm.doc.replication_and_binary_log) {
			prefix = 'replication-and-binary-log-';
		}
		frm.add_web_link(
			`${root}${prefix}system-variables/#${frm.doc.name}`,
			__('Check MariaDB Documentation')
		);
	},
});
