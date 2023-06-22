// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Replication', {
	setup: function (frm) {
		frm.set_query('site', function () {
			return {
				filters: {
					status: 'Active',
				},
			};
		});
	},
});
