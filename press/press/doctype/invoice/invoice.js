// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice', {
	refresh: function (frm) {
		if (frm.doc.stripe_invoice_id) {
			frm.add_web_link(`https://dashboard.stripe.com/invoices/${frm.doc.stripe_invoice_id}`, 'View Stripe Invoice')
		}
		if (frm.doc.frappe_invoice) {
			frm.add_web_link(`https://frappe.io/desk#Form/Sales Invoice/${frm.doc.frappe_invoice}`, 'View Frappe Invoice')
		}

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

		if (frm.doc.status == "Paid" && !frm.doc.frappe_invoice) {
			let btn = frm.add_custom_button(
				"Create Invoice on frappe.io",
				() => {
					frm.call({
						doc: frm.doc,
						method: "create_invoice_on_frappeio",
						btn,
					}).then(r => {
						if (r.message) {
							frappe.msgprint(`Sales Invoice ${r.message} created successfully.`)
						}
						frm.refresh()
					})
				}
			);
		}

		if (frm.doc.status == "Paid" && frm.doc.stripe_invoice_id) {
			let btn = frm.add_custom_button(
				"Refund Invoice",
				() => frappe.confirm(
					"This will refund the total amount paid on this invoice from Stripe. Continue?",
					() => frm.call({
						doc: frm.doc,
						method: "refund",
						btn,
					}).then(r => {
						if (r.message) {
							frappe.msgprint(`Refunded successfully.`)
						}
						frm.refresh()
					})
				)
			);
		}

		if (frm.doc.status == 'Invoice Created') {
			let btn = frm.add_custom_button(
				"Finalize",
				() => {
					frm.call({
						doc: frm.doc,
						method: "finalize_stripe_invoice",
						btn,
					}).then(r => frm.refresh())
				},
				'Stripe Invoice'
			);
		}

		if (frm.doc.docstatus == 1 && frm.doc.stripe_invoice_id) {
			let btn = frm.add_custom_button(
				"Change Status",
				() => {
					let d = new frappe.ui.Dialog({
						title: "Change Stripe Invoice Status",
						fields: [
							{
								label: 'Status',
								fieldname: 'status',
								fieldtype: 'Select',
								options: ['Paid', 'Uncollectible', 'Void']
							}
						],
						primary_action({ status }) {
							frm.call({
								doc: frm.doc,
								method: "change_stripe_invoice_status",
								args: {
									status
								},
								btn,
							}).then(r => frm.refresh())
						}
					});
					d.show();
				},
				"Stripe Invoice"
			);
		}
	},
});
