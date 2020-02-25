// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {	
	onload: function(frm) {
		frm.set_query("bench", function() {
			return {
				"filters": {
					"server": frm.doc.server,
				}
			};
		});
	},
	refresh: function(frm) {
		frm.add_web_link(`https://${frm.doc.name}`, __('Visit Site'));
		frm.add_custom_button(__('Agent Jobs'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Agent Job", filters);
		}, __('Logs'));
		frm.add_custom_button(__('Backups'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Site Backup", filters);
		}, __('Logs'));
		frm.add_custom_button(__('Site Uptime'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Site Uptime Log", filters);
		}, __('Logs'));
		frm.add_custom_button(__('Web Requests'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Site Request Log", filters);
		}, __('Logs'));
		frm.add_custom_button(__('Background Jobs'), () => {
			const filters = {site: frm.doc.name};
			frappe.set_route("List", "Site Job Log", filters);
		}, __('Logs'));
		frm.add_custom_button(__('Backup'), () => {
			frm.call({method: "perform_backup", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
		}, __('Actions'));
		frm.add_custom_button(__('Archive'), () => {
			frm.call({method: "archive", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
		}, __('Actions'));
	}
});
