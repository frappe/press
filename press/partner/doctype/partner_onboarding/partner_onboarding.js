frappe.ui.form.on('Partner Onboarding', {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== 'Pending Review') {
			return
		}

		frm.add_custom_button(__('Approve'), () => {
			frappe.confirm(__('Approve this partner onboarding request?'), () => {
				frm.call('approve').then(() => frm.refresh())
			})
		})

		frm.add_custom_button(__('Reject'), () => {
			frappe.prompt(
				[
					{
						fieldname: 'reason',
						fieldtype: 'Small Text',
						label: __('Reason'),
					},
				],
				(values) => {
					frm
						.call('reject', { reason: values.reason })
						.then(() => frm.refresh())
				},
				__('Reject partner onboarding request'),
				__('Reject'),
			)
		})
	},
})
