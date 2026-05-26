frappe.ui.form.on('Partner Onboarding', {
	refresh(frm) {
		if (frm.doc.status === 'Submission Pending') {
			frm.add_custom_button(__('Approve'), () => {
				frm.set_value('status', 'Approved')
				frm.save()
			})
			frm.add_custom_button(__('Reject'), () => {
				frm.set_value('status', 'Rejected')
				frm.save()
			})
		}
	},
})
