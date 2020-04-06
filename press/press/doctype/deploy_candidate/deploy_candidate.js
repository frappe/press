// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate', {
	refresh: function(frm) {
		frm.add_custom_button(__('Benches'), () => {
			const filters = {candidate: frm.doc.name};
			frappe.set_route("List", "Bench", filters);
		});
	}
});
