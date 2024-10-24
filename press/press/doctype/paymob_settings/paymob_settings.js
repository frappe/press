// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Paymob Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Get Access Token"), () => {
			frm.trigger("get_access_token")
		}).addClass("btn btn-primary")
	},
	get_access_token: function (frm) {
		try {
			frm.call({
				method: "get_access_token",
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Getting Access Token ...")
			}).then((r) => {
				if (!r.exc && r.message) {
					frm.set_value("token", r.message)
					frappe.show_alert({ message: __("Access Token Updated"), indicator: "green"});
				}
			});
		} catch(e) {
			console.log(e);
		}
	}
});
