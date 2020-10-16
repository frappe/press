// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Domain', {
	after_save: function (frm) {
		if (frm.doc.redirect_to_primary) {
			frm.call('setup_redirect');
		} else {
			frm.call('remove_redirect');
		}
	},
});
