// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Proxy Server', {
	refresh: function(frm) {
		frm.add_custom_button(__('Ping'), () => {
			frm.call({method: "ping", doc: frm.doc, callback: result => frappe.msgprint(result.message)});
		});
	}
});
