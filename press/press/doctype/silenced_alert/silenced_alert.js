// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Silenced Alert', {
	refresh(frm) {
		if (!frm.doc.__unsaved) {
			frm.add_custom_button('Preview Alerts filered by Instance', () => {
				frm.call('preview_alerts').then((r) => {
					if (r.message) {
						frappe.msgprint(r.message);
					} else {
						frm.refresh();
					}
				});
			});
		}
		if (!frm.doc.__unsaved && !frm.doc.silence_id) {
			frm.add_custom_button('Create Silence', () => {
				frm.call('create_new_silence').then((r) => {
					if (r.message) {
						frappe.msgprint(r.message);
					} else {
						frm.refresh();
					}
				});
			});
		}
	},
});
