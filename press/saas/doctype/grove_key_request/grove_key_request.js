// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Grove Key Request', {
	refresh(frm) {
		if (frm.doc.status === 'Failed') {
			frm.add_custom_button(__('Retry'), () =>
				frm.call('retry').then(() => frm.reload_doc()),
			)
		}
	},
})
