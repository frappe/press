// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release Approval Request', {
	status(frm) {
		frm.set_value('approved_by', frappe.session.user);
	},
});
