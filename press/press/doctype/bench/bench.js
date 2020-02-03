// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bench', {
	refresh: function(frm) {
		frm.add_custom_button(__('Sites'), () => {
			const filters = {bench: frm.doc.name};
			frappe.set_route("List", "Site", filters);
		});
		frm.add_custom_button(__('Jobs'), () => {
			const filters = {bench: frm.doc.name};
			frappe.set_route("List", "Agent Job", filters);
		});
	}
});
