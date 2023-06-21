// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Marketplace App Plan', {
	// refresh: function(frm) {
	// }
});
frappe.ui.form.on('Marketplace App Plan', {
	refresh: function (frm) {
		frm.set_query('standard_hosting_plan', () => {
			return {
				filters: { document_type: 'Site', is_trial_plan: 0 },
			};
		});
	},
});
