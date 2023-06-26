// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Update', {
	onload: function (frm) {
		frm.set_query('destination_bench', function () {
			return {
				'filters': {
					'status': 'Active',
					'server': frm.doc.server,
				}
			};
		});
	},
});
