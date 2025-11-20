// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payout Order', {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === 'Unpaid') {
			frm.add_custom_button(
				__('Mark as Paid'),
				function () {
					frappe.confirm(
						__('Are you sure you want to mark this payout order as paid?'),
						function () {
							frappe.call({
								method:
									'press.press.doctype.payout_order.payout_order.mark_as_paid',
								args: {
									payout_order: frm.doc.name,
								},
								callback: function (r) {
									if (!r.exc) {
										frm.reload_doc();
									}
								},
							});
						},
					);
				},
				__('Actions'),
			);
		}
	},
});
