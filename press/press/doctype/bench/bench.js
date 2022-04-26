// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bench', {
	onload: function (frm) {
		frm.set_query("candidate", function () {
			return {
				"filters": {
					"group": frm.doc.group,
				}
			};
		});
	},

	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.group}/versions/${frm.doc.name}`,
			__('Visit Dashboard')
		);

		[
			[__('Archive'), 'archive'],
			[__('Sync Sites Info'), 'sync_info'],
			[__('Update All Sites'), 'update_all_sites'],
			[__('Remove SSH User from Proxy'), 'remove_ssh_user', frm.doc.is_ssh_proxy_setup],
			[__('Add SSH User to Proxy'), 'add_ssh_user', !frm.doc.is_ssh_proxy_setup],
			[__('Restart'), 'restart', frm.doc.status === "Active"],
		].forEach(([label, method, condition]) => {
			if (typeof condition === "undefined" || condition){	
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()} this bench?`,
							() => frm.call(method).then((r) => frm.refresh())
						);
					},
					__('Actions')
				);
			}
		});

		frm.add_custom_button(
			'Move sites',
			() => {
				let d = new frappe.ui.Dialog({
					title: 'Move sites',
					fields: [
						{
							fieldtype: 'Link',
							fieldname: 'server',
							label: 'Server',
							options: 'Server',
							reqd: 1,
						},
					],
					primary_action({ server }) {
						frm.call('move_sites', { server }).then((r) => {
							if (!r.exc) {
								frappe.show_alert(`Scheduled migrations for sites to ${server}`);
							}
							d.hide()
						});
					},
				});
				d.show();
			},
			__('Actions')
		);

	}
});
