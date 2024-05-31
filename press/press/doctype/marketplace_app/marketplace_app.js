// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Marketplace App', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/apps/${frm.doc.name}/`,
			__('Open in dashboard'),
		);
	},
});
