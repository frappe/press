// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Team', {
	refresh: function (frm) {
		frm.add_custom_button(
			'Suspend Sites',
			() => {
				frappe.prompt(
					{ fieldtype: 'Data', label: 'Reason', fieldname: 'reason', reqd: 1 },
					({ reason }) => {
						frm.call('suspend_sites', { reason }).then((r) => {
							const sites = r.message;
							let how_many = 'No';
							if (sites) {
								how_many = sites.length;
							}
							frappe.show_alert(`${how_many} sites were suspended.`);
						});
					}
				);
			},
			'Actions'
		);
		frm.add_custom_button(
			'Unsuspend Sites',
			() => {
				frappe.prompt(
					{ fieldtype: 'Data', label: 'Reason', fieldname: 'reason', reqd: 1 },
					({ reason }) => {
						frm.call('unsuspend_sites', { reason }).then((r) => {
							const sites = r.message;
							let how_many = 'No';
							if (sites) {
								how_many = sites.length;
							}
							frappe.show_alert(`${how_many} sites were unsuspended.`);
						});
					}
				);
			},
			'Actions'
		);
	},
});
