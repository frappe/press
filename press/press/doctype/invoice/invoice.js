// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice', {
	refresh: function (frm) {
		if (frm.doc.stripe_invoice_id) {
			frm.add_web_link(
				`https://dashboard.stripe.com/invoices/${frm.doc.stripe_invoice_id}`,
				'View Stripe Invoice'
			);
		}
		if (frm.doc.frappe_invoice) {
			frm.add_web_link(
				`https://frappe.io/app/sales-invoice/${frm.doc.frappe_invoice}`,
				'View Frappe Invoice'
			);
		}

		if (frm.doc.frappe_partner_order) {
			frm.add_web_link(
				`https://frappe.io/app/partner-order/${frm.doc.frappe_partner_order}`,
				'View Frappe Partner Order'
			);
		}

		if (frm.doc.status == 'Paid' && !frm.doc.frappe_invoice) {
			let btn = frm.add_custom_button('Create Invoice on frappe.io', () => {
				frm
					.call({
						doc: frm.doc,
						method: 'create_invoice_on_frappeio',
						btn,
					})
					.then((r) => {
						if (r.message) {
							frappe.msgprint(
								`Sales Invoice ${r.message} created successfully.`
							);
						}
						frm.refresh();
					});
			});
		}

		if (frm.doc.status == 'Paid' && frm.doc.stripe_invoice_id) {
			let btn = frm.add_custom_button('Refund Invoice', () =>
				frappe.confirm(
					'This will refund the total amount paid on this invoice from Stripe. Continue?',
					() =>
						frm
							.call({
								doc: frm.doc,
								method: 'refund',
								btn,
							})
							.then((r) => {
								if (r.message) {
									frappe.msgprint(`Refunded successfully.`);
								}
								frm.refresh();
							})
				)
			);
		}

		if (frm.doc.status == 'Invoice Created') {
			let btn = frm.add_custom_button(
				'Finalize Invoice',
				() => {
					frappe.confirm(
						"This action will finalize the Stripe Invoice and charge the customer's card. Continue?",
						() => {
							frm
								.call({
									doc: frm.doc,
									method: 'finalize_stripe_invoice',
									btn,
								})
								.then((r) => frm.refresh());
						}
					);
				},
				'Stripe Invoice'
			);
		}

		if (frm.doc.stripe_invoice_url) {
			let btn = frm.add_custom_button(
				'Refresh Payment Link',
				() => {
					frm
						.call({
							doc: frm.doc,
							method: 'refresh_stripe_payment_link',
							btn,
						})
						.then((r) => {
							frm.refresh();
							console.log(r.message);
							frappe.utils.copy_to_clipboard(r.message);
							frappe.msgprint({
								title: 'Stripe Payment Link Updated',
								indicator: 'green',
								message: 'The Link has been copied to the clipboard.',
							});
						});
				},
				'Stripe Invoice'
			);
		}

		if (frm.doc.docstatus == 1 && frm.doc.stripe_invoice_id) {
			let btn = frm.add_custom_button(
				'Change Status',
				() => {
					let d = new frappe.ui.Dialog({
						title: 'Change Stripe Invoice Status',
						fields: [
							{
								label: 'Status',
								fieldname: 'status',
								fieldtype: 'Select',
								options: ['Paid', 'Uncollectible', 'Void'],
							},
						],
						primary_action({ status }) {
							frm
								.call({
									doc: frm.doc,
									method: 'change_stripe_invoice_status',
									args: {
										status,
									},
									btn,
								})
								.then((r) => frm.refresh());
						},
					});
					d.show();
				},
				'Stripe Invoice'
			);
		}

		if (frm.doc.docstatus === 0) {
			let btn = frm.add_custom_button('Finalize Invoice', () =>
				frappe.confirm(
					'This action will apply credits (if applicable) and generate a Stripe invoice if the amount due is greater than 0. ' +
						'If a Stripe invoice was generated already, it will be voided and a new one will be generated. Continue?',
					() =>
						frm
							.call({
								doc: frm.doc,
								method: 'finalize_invoice',
								btn,
							})
							.then(() => {
								frm.refresh();
							})
				)
			);
		}
	},
});
