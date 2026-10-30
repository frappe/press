// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Enterprise Contract', {
	refresh(frm) {
		if (frm.doc.status === 'Awaiting Payment' && frm.doc.transfer_reference) {
			frm.add_custom_button(__('Confirm Bank Transfer'), () =>
				frappe.confirm(
					__('Is UTR {0} on the bank statement for the full amount?', [
						frm.doc.transfer_reference,
					]),
					() => frm.call('confirm_bank_transfer').then(() => frm.reload_doc()),
				),
			)
		}
	},
})
