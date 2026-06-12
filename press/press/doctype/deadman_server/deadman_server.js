// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deadman Server', {
	refresh(frm) {
		if (!frm.doc.is_server_setup) {
			frm.add_custom_button(
				__('Setup Server'),
				() => {
					frappe.confirm(__('Are you sure you want to setup server?'), () =>
						frm.call('setup_server').then((r) => {
							if (r.message) {
								frappe.msgprint(r.message)
							} else {
								frm.refresh()
							}
						}),
					)
				},
				__('Actions'),
			)
		}
	},
})
