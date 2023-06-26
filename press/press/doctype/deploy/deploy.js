// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy', {
	onload: function (frm) {
		frm.set_query('candidate', function () {
			return {
				filters: {
					group: frm.doc.group,
				},
			};
		});
	},
	// refresh: function(frm) {

	// }
});
