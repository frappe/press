// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Enterprise Contract', {
	refresh(frm) {
		// Due for a new order, or for a renewal once its window is open. Card renewals are the
		// customer's to make on the dashboard; staff record bank transfers only.
		if (
			!frm.perm[0]?.write ||
			!frm.doc.__onload?.payment_due ||
			frm.doc.payment_gateway !== 'Bank Transfer'
		)
			return
		const utr = frm.doc.__onload.pending_transfer_reference
		if (utr) {
			frm.add_custom_button(__('Confirm Bank Transfer'), () =>
				frappe.confirm(
					__('Is UTR {0} on the bank statement for the full amount?', [utr]),
					() => confirm_transfer(frm),
				),
			)
		} else {
			frm.add_custom_button(__('Record Bank Transfer'), () =>
				frappe.prompt(
					{
						fieldname: 'reference',
						fieldtype: 'Data',
						label: __('UTR on the bank statement'),
						reqd: 1,
					},
					({ reference }) => confirm_transfer(frm, reference),
					__('Record Bank Transfer'),
					__('Record'),
				),
			)
		}
	},
})

function confirm_transfer(frm, reference) {
	frm
		.call('confirm_bank_transfer', reference ? { reference } : {})
		.then(() => frm.reload_doc())
}
