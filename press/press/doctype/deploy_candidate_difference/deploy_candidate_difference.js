// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate Difference', {
	onload: function (frm) {
		frm.set_query('source', function () {
			return {
				filters: {
					group: frm.doc.group,
				},
			};
		});
		frm.set_query('destination', function () {
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
