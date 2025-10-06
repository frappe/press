// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('NFS Server', {
	refresh(frm) {
		[
			[
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
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
		if (frm.doc.status === 'Active') {
			frm.add_custom_button('Add Mount Enabled Server', () => {
				frappe.prompt(
					[
						{
							fieldtype: 'Link',
							fieldname: 'server',
							label: 'Server',
							options: 'Server',
							reqd: 1,
						},
						{
							fieldtype: 'Int',
							fieldname: 'volume_size',
							label: 'Volume Size',
						},
					],
					({
						server,
						share_file_system,
						use_file_system_of_server,
						move_benches,
						volume_size,
					}) => {
						frm
							.call('add_mount_enabled_server', {
								server: server,
								share_file_system: share_file_system,
								move_benches: move_benches,
								volume_size: volume_size,
								use_file_system_of_server: use_file_system_of_server,
							})
							.then((r) => {
								frm.refresh();
							});
					},
				);
			});
		}
		if (frm.doc.status === 'Active') {
			frm.add_custom_button('Remove Mount Enabled Server', () => {
				frappe.prompt(
					[
						{
							fieldtype: 'Link',
							fieldname: 'server',
							label: 'Server',
							options: 'Server',
							reqd: 1,
						},
					],
					({ server }) => {
						frm
							.call('remove_mount_enabled', {
								server: server,
							})
							.then((r) => {
								frm.refresh();
							});
					},
				);
			});
		}
	},
});
