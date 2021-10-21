// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Marketplace App Subscription', {
	refresh: function (frm) {
		if (frm.doc.status != 'Active') {
			frm.add_custom_button(
				__('Activate'),
				() => {
					frm.call('activate').then(() => {
						frappe.msgprint({
							title: 'Subscription Activated successfully.',
							indicator: 'green',
						});
						frm.refresh();
					});
				},
				'Actions'
			);
		}
	},
});
