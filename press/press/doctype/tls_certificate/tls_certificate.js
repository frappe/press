// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('TLS Certificate', {
	refresh: function (frm) {
		frm.add_custom_button(__('Obtain Certificate'), () => {
			frm.call({
				method: "obtain_certificate",
				doc: frm.doc,
				callback: result => frm.refresh()
			});
		});
	}
});