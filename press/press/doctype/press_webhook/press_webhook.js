// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Press Webhook', {
	refresh(frm) {
		let webhook = frm.get_doc();

		if (!webhook.enabled) {
			frm.add_custom_button(
				__('Activate'),
				() => {
					frm.call('activate').then((r) => {
						if (r.message) {
							frappe.msgprint(r.message);
						}
					});
				},
				__('Actions'),
			);
		} else {
			frm.add_custom_button(
				__('Disable'),
				() => {
					frm.call('disable').then((r) => {
						if (r.message) {
							frappe.msgprint(r.message);
						}
					});
				},
				__('Actions'),
			);

			frm.add_custom_button(
				__('Disable and Notify'),
				() => {
					frm.call('disable_and_notify').then((r) => {
						if (r.message) {
							frappe.msgprint(r.message);
						}
					});
				},
				__('Actions'),
			);
		}
	},
});
