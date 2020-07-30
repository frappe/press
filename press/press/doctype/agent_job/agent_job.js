// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agent Job', {
	refresh: function (frm) {
		frm.add_custom_button(__('Retry'), () => {
			frm.call({method: "retry", doc: frm.doc, callback: result => frappe.msgprint(result.message.name)});
		});
	}
});
