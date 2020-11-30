// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate', {
	refresh: function (frm) {
		frm.add_custom_button(
			__('Build'),
			() => {
				frm.call("build").then(() => frm.refresh());
			},
			__('Actions')
		);
	}
});
