// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release', {
	refresh: function (frm) {
		if (!frm.doc.cloned) {
			frm.add_custom_button(
				__('Clone'),
				() => {
					frm.call("clone").then((r) => frappe.msgprint(r.message));
				},
			);
		} else {
			frm.add_custom_button(
				__('View'),
				() => {
					window.open(frm.doc.code_server_url);
				},
			);
		}
	},
});
