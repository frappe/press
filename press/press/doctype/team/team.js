// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Team', {
	refresh: function (frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Team' };
		frappe.contacts.render_address_and_contact(frm);

		frm.add_custom_button('Enable Partner Privileges',
			() => frappe.confirm(`Enable ERPNext Partner Privileges for ${frm.doc.name.bold()}? They will be allowed to create sites without adding a card and can transfer credits from ERPNext.com`,
				() => frm.call('enable_erpnext_partner_privileges')
			),
		);

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

		frm.add_custom_button('Impersonate Team', () => {
			let team = frm.doc.name;
			window.open(`/dashboard/impersonate/${team}`);
		});
	},

});

frappe.ui.form.on('Team Member', {
	impersonate: function (frm, doctype, member) {
		frappe.prompt(
			[
				{ fieldtype: 'HTML', options: "Beware! Your current session will be replaced." },
				{ fieldtype: 'Text Editor', label: 'Reason', fieldname: 'reason', reqd: 1 }],
			({ reason }) => {
				frm.call('impersonate', { reason, member }).then((r) => {
					location.href = "/dashboard";
				});
			},
			"Impersonate User"
		);
	}
});
