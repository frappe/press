// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Proxy Failover', {
	refresh(frm) {
		if (frm.doc.status != "Success") {
			frm.add_custom_button(
				'Force Continue',
				() => {
					frm.call('force_continue');
				},
				'Actions',
			);
		}
	},
});
