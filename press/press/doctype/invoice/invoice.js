// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice', {
	refresh: function (frm) {
		if (frm.doc.status === 'Unpaid') {
			frm.add_custom_button('Mark as Paid', () => {
				let d = new frappe.ui.Dialog({
					title: 'Mark as Paid',
					fields: [
						{
							fieldtype: 'HTML',
							options:
								'This action will consume credits and mark this invoice as Paid if enough credits are available. Will fail if not.',
						},
						{
							fieldtype: 'Text',
							fieldname: 'reason',
							label: 'Reason',
						},
					],
					primary_action({ reason }) {
						frm
							.call({
								doc: frm.doc,
								method: 'consume_credits_and_mark_as_paid',
								args: { reason },
								btn: d.get_primary_btn(),
							})
							.then((r) => {
								if (!r.exc) {
									frappe.show_alert('Success');
								}
								d.hide();
							});
					},
				});
				d.show();
			});
		}
	},
});
