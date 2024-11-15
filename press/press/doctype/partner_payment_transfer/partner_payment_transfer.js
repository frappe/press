// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Partner Payment Transfer", {
    refresh(frm) {
        if(frm.doc.docstatus == 0) {
        frm.add_custom_button("Fetch Payments", () => {
            frappe.call({
                method: "press.press.doctype.partner_payment_transfer.partner_payment_transfer.fetch_payments",
                args: {
                    transaction_doctype: frm.doc.transaction_doctype,
                    from_date: frm.doc.from_date,
                    to_date: frm.doc.to_date,
                },
                callback: function(response) {
                    if (response.message) {
                        // Clear existing entries in transfer_items
                        frm.clear_table("transfer_items");

                        response.message.forEach(payment => {
                            let row = frm.add_child("transfer_items");
                            row.transaction_id = payment.name;
                            row.posting_date=payment.posting_date
                            row.amount = payment.amount_usd;

                        });

                        frm.refresh_field("transfer_items");
                        frappe.msgprint("Payments fetched and added to the transfer items table.");
                    }
                }
            });
        });
    }},
});

