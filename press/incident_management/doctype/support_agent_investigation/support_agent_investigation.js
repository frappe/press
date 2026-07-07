// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Support Agent Investigation', {
	refresh(frm) {
		if (frm.doc.status === 'Completed') {
			frm.add_custom_button(__('Get AI Analysis'), () => {
				frappe.confirm(
					__(
						'This will send the redacted investigation payload to Claude. No customer PII is included. Continue?',
					),
					() => {
						frm.call({
							method: 'run_llm_analysis',
							freeze: true,
							freeze_message: __('Sending to Claude…'),
							callback(r) {
								if (!r.exc) {
									frm.reload_doc()
								}
							},
						})
					},
				)
			})
		}
	},
})
