// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Ledger Entry', {
	refresh(frm) {
		if (frm.doc.purpose == 'Credits Allocation' && !frm.doc.reverted) {
			frm.add_custom_button(__('Revert'), () => {
				frappe.prompt(
					{
						label: __('Reason'),
						fieldtype: 'Small Text',
						fieldname: 'reason',
					},
					({ reason }) => {
						frm.call('revert', { reason });
					},
					__('Reason for revert')
				);
			});
		}
	},
});
