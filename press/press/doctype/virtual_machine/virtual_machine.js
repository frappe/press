// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine', {
	refresh: function (frm) {
		if (frm.doc.status == "Pending") {
			frm.add_custom_button(
				"Poll Pending Machines",
				() => {
					frappe.call("press.press.doctype.virtual_machine.virtual_machine.poll_pending_machines").then(r => frm.refresh());
				},
				__('Actions')
			);
		}
	}
});
