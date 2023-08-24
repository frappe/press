// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Version Upgrade', {
	refresh: function (frm) {
		if (['Scheduled', 'Failure'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Start'), () => {
				frappe.confirm('Are you sure you want to try an update?', () =>
					frm.call('start'),
				);
			});
		}
		if (frm.doc.status == 'Success') {
			frm.add_custom_button(__('Show on FC'), () => {
				window.open(`https://frappecloud.com/dashboard/sites/${frm.doc.site}`);
			});
		}
	},
});
