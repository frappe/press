// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server', {
	refresh: function(frm) {
		frm.add_custom_button(__('Benches'), () => {
			const filters = {bench: frm.doc.name};
			frappe.set_route("List", "Bench", filters);
		});
		frm.add_custom_button(__('Jobs'), () => {
			const filters = {server: frm.doc.name};
			frappe.set_route("List", "Agent Job", filters);
		});
		frm.add_custom_button(__('Ping'), () => {
			frm.call({method: "ping", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
		}, __("Actions"));
		frm.add_custom_button(__('Update Agent'), () => {
			frm.call({method: "update_agent", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
		}, __("Actions"));
		if (!frm.doc.is_server_setup) {
			frm.add_custom_button(__('Setup Server'), () => {
				frm.call({method: "setup_server", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
			}, __("Actions"));
		}
		if (!frm.doc.is_upstream_setup) {
			frm.add_custom_button(__("Add to Proxy"), () => {
				frm.call({method: "add_upstream_to_proxy", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
			}, __("Actions"));
		}
}
});
