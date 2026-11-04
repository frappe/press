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
		if (frm.doc.status !== 'Assigned') return
		frm.add_custom_button(__('Raise Cap'), () =>
			frappe.prompt(
				{
					fieldname: 'cap',
					fieldtype: 'Currency',
					label: __('New cap (USD)'),
					default: frm.doc.cap,
					reqd: 1,
				},
				(values) =>
					frm
						.call({
							doc: frm.doc,
							method: 'raise_cap',
							args: { cap: values.cap },
							freeze: true,
						})
						.then(() => frm.reload_doc()),
				__('Raise Cap'),
				__('Raise'),
			),
		)
	},
})
