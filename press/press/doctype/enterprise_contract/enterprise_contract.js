// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Enterprise Contract', {
	refresh(frm) {
		if (
			!frm.perm[0]?.write ||
			frm.doc.status !== 'Awaiting Payment' ||
			frm.doc.payment_gateway !== 'Bank Transfer'
		)
			return
		if (frm.doc.transfer_reference) {
			frm.add_custom_button(__('Confirm Bank Transfer'), () =>
				frappe.confirm(
					__('Is UTR {0} on the bank statement for the full amount?', [
						frm.doc.transfer_reference,
					]),
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
