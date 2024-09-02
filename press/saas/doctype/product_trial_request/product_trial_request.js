// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Product Trial Request', {
	refresh(frm) {
		frm.add_custom_button(__('Preview Setup Wizard Payload'), function () {
			frappe.call({
				method: 'get_setup_wizard_payload',
				doc: frm.doc,
				args: {},
				freeze: true,
				freeze_message: __('Generating Setup Wizard Payload'),
				callback: function (r) {
					if (r.exc) {
						frappe.msgprint(r.exc);
					} else {
						frappe.msgprint({
							title: __('Setup Wizard Payload'),
							message: JSON.stringify(r.message, null, 4),
						});
					}
				},
				error: function (r) {
					frappe.msgprint(r.message);
				},
			});
		});
	},
});
