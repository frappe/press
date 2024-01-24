// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB Variable', {
	refresh(frm) {
		let root = 'https://mariadb.com/kb/en/';
		frm.add_web_link(
			`${root}${frm.doc.doc_section}-system-variables/#${frm.doc.name}`,
			__('Check MariaDB Documentation'),
		);
		frm.add_custom_button(__('Set on all servers'), () => {
			frappe.confirm(
				`Are you sure you want to set variable on all servers?
								If variable is not dynamic, mariadb will be restarted`,
				() =>
					frm.call('set_on_all_servers').then((r) => {
						if (r.message) {
							frappe.msgprint(r.message);
						} else {
							frm.refresh();
						}
					}),
			);
		});
	},
});
