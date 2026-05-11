// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cluster Registry", {
	refresh(frm) {
		frm.add_custom_button(
			__("Setup Project"),
			() => {
				frm.call("setup_project").then((_r) => frm.refresh());
			},
			__("Actions"),
		);

		frm.add_custom_button(
			__("Show Admin Password"),
			() => {
				frm.call("show_admin_password").then((r) => {
					frappe.msgprint(r.message);
				});
			},
			__("Actions"),
		);

		frm.add_custom_button(
			__("Trigger Garbage Collection"),
			() => {
				frm.call("trigger_garbage_collection").then((_r) => {
					frappe.msgprint(__("Garbage collection triggered successfully."));
				});
			},
			__("Actions"),
		);

		frm.add_web_link(
			`https://${frm.doc.name}/harbor/projects`,
			__("Visit Harbor Dashboard"),
		);
	},
});
