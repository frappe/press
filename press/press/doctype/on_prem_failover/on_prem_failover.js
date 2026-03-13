// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('On-Prem Failover', {
	refresh(frm) {
		[
			[
				'Setup Wireguard on App Server',
				'setup_wireguard_on_app_server',
				false,
				frm.doc.enabled,
			],
			[
				'Setup Wireguard on Database Server',
				'setup_wireguard_on_database_server',
				false,
				frm.doc.enabled,
			],
			[
				'View On-Prem Wireguard Config',
				'view_on_prem_server_wireguard_config',
				false,
				frm.doc.enabled,
			],
			[
				'View On-Prem SSH Authorized Keys',
				'view_on_prem_server_ssh_authorized_keys',
				false,
				frm.doc.enabled,
			],
			[
				'Test Connectivity to On-Premise Server',
				'test_connectivity_to_on_premise_server',
				false,
				frm.doc.enabled,
			],
			[
				'Setup DB Lsync for Initial Sync',
				'setup_db_lsync_for_initial_sync',
				true,
				frm.doc.enabled,
			],
			[
				'Setup DB Rsync for Final Sync',
				'setup_db_rsync_for_final_sync',
				true,
				frm.doc.enabled,
			],
			[
				'Setup Replica on On-Prem',
				'setup_replica_on_prem',
				true,
				frm.doc.enabled,
			],
			[
				'Setup App Server Replica',
				'setup_app_server_replica',
				true,
				frm.doc.enabled,
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
	},
});
