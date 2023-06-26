// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release Approval Request', {
	refresh(frm) {
		if (['Open', 'Rejected'].includes(frm.doc.status)) {
			frm.add_custom_button('Approve Request', () => {
				frm.set_value('status', 'Approved');
				frm.save();
			});
		}

		if (!frm.doc.result && frm.doc.screening_status === 'Not Started') {
			let btn = frm.add_custom_button('Screen Release', () => {
				frm.call('start_screening');
				frappe.msgprint('Started Screening')
			});
		}

		if (frm.doc.result_html) {
			let wrapper = frm.get_field('result_html_rendered').$wrapper;
			wrapper.html(frm.doc.result_html);
		}
	},
	status(frm) {
		frm.set_value('reviewed_by', frappe.session.user);
	},
});
