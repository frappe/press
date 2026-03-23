// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Marketplace App Audit', {
	refresh(frm) {
		// a button to re-run the same audit
		frm.add_custom_button(__('Re-run Audit'), () => {
			frm
				.call('rerun_audit', {
					doc: frm.doc,
				})
				.then((r) => {
					frappe.msgprint('Audit re-run successfully: ' + r.message);
					frm.refresh();
				});
		});
	},
});
