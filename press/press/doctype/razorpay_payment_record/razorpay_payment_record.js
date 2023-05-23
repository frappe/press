// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Razorpay Payment Record', {
	refresh: function(frm) {
		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Sync"), function() {
				frm.call("sync").then(() => {
					frm.refresh();
				});
			});
		}
	}
});
