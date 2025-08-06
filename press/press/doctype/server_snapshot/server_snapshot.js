// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server Snapshot', {
	refresh(frm) {
		[
			[__('Sync'), 'sync', false, true],
			[
				__('Delete'),
				'delete_snapshots',
				true,
				['Pending', 'Completed'].includes(frm.doc.status),
			],
			[__('Unlock'), 'unlock', true, frm.doc.locked],
			[__('Lock'), 'lock', true, !frm.doc.locked],
			[
				__('Recover All Sites'),
				'recover_sites',
				true,
				frm.doc.status === 'Completed',
			],
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (confirm) {
							frappe.confirm(
								`Are you sure you want to ${label.toLowerCase()}?`,
								() =>
									frm.call(method).then((r) => {
										if (r.message) {
											frappe.msgprint(r.message);
										} else {
											frm.refresh();
										}
									}),
							);
						} else {
							frm.call(method).then((r) => {
								if (r.message) {
									frappe.msgprint(r.message);
								} else {
									frm.refresh();
								}
							});
						}
					},
					__('Actions'),
				);
			}
		});

		if (frm.doc.status === 'Completed') {
			frm.add_custom_button(
				'Create Server',
				() => {
					frappe.prompt(
						[
							{
								fieldtype: 'Link',
								label: 'Team',
								fieldname: 'team',
								options: 'Team',
								reqd: 1,
								default: frm.doc.team,
							},
							{
								fieldtype: 'Select',
								label: 'Server Type',
								fieldname: 'server_type',
								options: ['Server', 'Database Server'],
								reqd: 1,
								default: 'Server',
							},
							{ fieldtype: 'Data', label: 'Server Name', fieldname: 'title' },
							{
								fieldtype: 'Link',
								label: 'Server Plan',
								fieldname: 'plan',
								options: 'Server Plan',
								reqd: 0,
								get_query: function () {
									return {
										filters: {
											cluster: frm.doc.cluster,
											enabled: 1,
											premium: 0,
										},
									};
								},
							},
							{
								fieldtype: 'Check',
								label: 'Create Subscription',
								fieldname: 'create_subscription',
							},
							{
								fieldtype: 'Check',
								label: 'Is Temporary Server ?',
								fieldname: 'temporary_server',
								default: 1,
							},
						],
						({
							team,
							server_type,
							title,
							plan,
							create_subscription,
							temporary_server,
						}) => {
							frm
								.call('create_server', {
									team,
									server_type,
									title,
									plan,
									create_subscription,
									temporary_server,
								})
								.then((r) => frm.refresh());
						},
					);
				},
				__('Actions'),
			);
		}
	},
});
