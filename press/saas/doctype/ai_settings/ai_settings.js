// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

const METHODS = 'press.saas.doctype.ai_settings.ai_settings'

frappe.ui.form.on('AI Settings', {
	refresh(frm) {
		if (frm.doc.control_api_key) {
			frm.add_custom_button(__('Rotate Credential'), () => rotate(frm))
		} else {
			frm.add_custom_button(__('Enroll'), () => enroll(frm))
		}
	},
})

function enroll(frm) {
	if (frm.is_dirty()) {
		frappe.msgprint(__('Save the settings before enrolling.'))
		return
	}
	frappe.prompt(
		{
			fieldname: 'bootstrap_secret',
			label: __('Bootstrap Secret'),
			fieldtype: 'Password',
			reqd: 1,
		},
		({ bootstrap_secret }) =>
			// A plain call: its arguments arrive at the top of the request, where the secret is
			// popped before anything logs it.
			frappe
				.call({ method: `${METHODS}.enroll`, args: { bootstrap_secret } })
				.then(() => {
					frappe.show_alert({ message: __('Enrolled.'), indicator: 'green' })
					frm.reload_doc()
				}),
		__('Enroll at Grove'),
		__('Enroll'),
	)
}

function rotate(frm) {
	frappe.confirm(
		__('Issue a new control secret? The current one stops working at once.'),
		() =>
			frappe.call({ method: `${METHODS}.rotate_credential` }).then(() => {
				frappe.show_alert({ message: __('Rotated.'), indicator: 'green' })
				frm.reload_doc()
			}),
	)
}
