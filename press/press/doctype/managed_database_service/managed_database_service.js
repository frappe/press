// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Managed Database Service', {
	refresh(frm) {
		let command = `mysql -h ${frm.doc.name} -p -u ${frm.doc.database_root_user} -P ${frm.doc.port}`;
		frm.add_custom_button('Console Access', () => {
			frappe.msgprint(`<pre>${command}</pre>`);
		});
		frm.add_custom_button('Show Root Password', () => {
			frm.call('show_root_password').then((r) => {
				frappe.msgprint(`<pre>${r.message}<pre>`);
			});
		});
	},
});
