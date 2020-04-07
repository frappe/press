// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Group', {
	refresh: function(frm) {
		frm.add_custom_button(__('Deploy Candidates'), () => {
			const filters = {group: frm.doc.name};
			frappe.set_route("List", "Deploy Candidate", filters);
		});
		frm.add_custom_button(__('Benches'), () => {
			const filters = {group: frm.doc.name};
			frappe.set_route("List", "Bench", filters);
		});
	}
});
