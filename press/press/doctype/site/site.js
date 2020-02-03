// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {
	refresh: function(frm) {
		frm.add_custom_button(__('Jobs'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Agent Job", filters);
		});
		frm.add_custom_button(__('Backups'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Site Backup", filters);
		});
		frm.add_custom_button(__('Backup'), () => {
			frm.call({method: "perform_backup", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
		});
	}
});
