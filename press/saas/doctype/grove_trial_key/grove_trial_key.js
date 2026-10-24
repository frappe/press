// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Grove Trial Key', {
	refresh(frm) {
		if (frm.is_new() || !['Available', 'Assigned'].includes(frm.doc.status))
			return

		const message =
			frm.doc.status === 'Assigned'
				? __('Revoke this key at Grove? Its trial site can no longer call AI.')
				: __('Revoke this key at Grove?')
		frm.add_custom_button(__('Revoke Key'), () =>
			frappe.confirm(message, () =>
				frm
					.call({ doc: frm.doc, method: 'revoke', freeze: true })
					.then(() => frm.reload_doc()),
			),
		)
	},
})
