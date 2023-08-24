// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Team Deletion Request', {
	onload: function (frm) {
		frappe.realtime.on('doc_update', (data) => {
			if (!frm.is_dirty()) {
				frm.reload_doc();
			}
		});
	},
});
