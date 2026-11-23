// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Backup Daily Audit', {
	refresh(frm) {
		frm.add_custom_button(__('Refresh'), () =>
			frm
				.call('refresh_lists')
				.then(() =>
					frappe.show_alert(
						__(
							'Refreshing in the background. Reload this page in a few minutes.',
						),
					),
				),
		)
	},
})
