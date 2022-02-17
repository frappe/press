// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Central Site Migration', {
	refresh: function (frm) {
		if (['Scheduled', 'Failure', 'Success'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Start'), () => {
				frappe.confirm('Are you sure you want to retry the migration?', () =>
					frm.call('start')
				);
			});
		}
	},
});
