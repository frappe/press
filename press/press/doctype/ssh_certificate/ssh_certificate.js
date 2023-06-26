// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('SSH Certificate', {
	refresh: function (frm) {
		frm.set_query('user_ssh_key', () => {
			return {
				filters: { user: frm.doc.user },
			};
		});
	}
});
