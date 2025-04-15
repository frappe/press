// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Partner Payment Payout', {
	refresh(frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button('Fetch Payments', () => {
				frappe.call({
					method: 'press.api.regional_payments.mpesa.utils.fetch_payments',
					args: {
						// transaction_doctype: frm.doc.transaction_doctype,
						from_date: frm.doc.from_date,
						to_date: frm.doc.to_date,
						partner: frm.doc.partner,
						payment_gateway: frm.doc.payment_gateway,
					},
					callback: function (response) {
						if (response.message) {
							// Clear existing entries in transfer_items
							frm.clear_table('transfer_items');

							response.message.forEach((payment) => {
								let row = frm.add_child('transfer_items');
								row.transaction_id = payment.name;
								row.posting_date = payment.posting_date;
								row.amount = payment.amount;
							});

							frm.refresh_field('transfer_items');
							// frappe.msgprint("Payments fetched and added to the transfer items table.");
						}
					},
				});
			});
		}
	},
});
