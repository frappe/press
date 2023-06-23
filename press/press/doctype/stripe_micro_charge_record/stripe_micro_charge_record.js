// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stripe Micro Charge Record', {
	refresh: function (frm) {
		if (!frm.doc.has_been_refunded) {
			const btn = frm.add_custom_button('Refund', () => {
				frm
					.call({
						doc: frm.doc,
						method: 'refund',
						btn,
					})
					.then((r) => {
						if (r.message) {
							frappe.msgprint(`Refunded Successfully.`);
						}
						frm.refresh();
					});
			});
		}

		frm.add_web_link(
			`https://dashboard.stripe.com/payments/${frm.doc.stripe_payment_intent_id}`,
			'View in Stripe Dashboard',
		);
	},
});
