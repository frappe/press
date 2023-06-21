// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('TLS Certificate', {
	refresh: function (frm) {
		frm.add_custom_button(__('Obtain Certificate'), () => {
			frm.call({
				method: 'obtain_certificate',
				doc: frm.doc,
				callback: (result) => frm.refresh(),
			});
		});
		if (frm.doc.wildcard) {
			frm.add_custom_button(__('Trigger Callback'), () => {
				frm.call({
					method: 'trigger_server_tls_setup_callback',
					doc: frm.doc,
					callback: (result) => frm.refresh(),
				});
			});
		}
	},
});
