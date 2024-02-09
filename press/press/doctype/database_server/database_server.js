// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Database Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		[
			[__('Ping Agent'), 'ping_agent', false, !frm.doc.is_server_setup],
			[__('Ping Ansible'), 'ping_ansible', true, frm.doc.is_server_prepared],
			[
				__('Ping Ansible Unprepared'),
				'ping_ansible_unprepared',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Update Agent'), 'update_agent', true, frm.doc.is_server_setup],
			[
				__('Update Agent Ansible'),
				'update_agent_ansible',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Fetch Keys'),
				'fetch_keys',
				true,
				frm.doc.is_server_setup &&
					(!frm.doc.frappe_public_key || !frm.doc.root_public_key),
			],
			[
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[
				__('Setup Rename'),
				'rename_server',
				true,
				frm.doc.is_server_setup &&
					frm.doc.is_server_prepared &&
					!frm.doc.is_server_renamed,
			],
			[
				__('Convert From Frappe Server'),
				'convert_from_frappe_server',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Setup Replication'),
				'setup_replication',
				true,
				frm.doc.is_server_setup &&
					!frm.doc.is_primary &&
					!frm.doc.is_replication_setup,
			],
			[
				__('Trigger Failover'),
				'trigger_failover',
				true,
				frm.doc.is_server_setup &&
					!frm.doc.is_primary &&
					frm.doc.is_replication_setup,
			],
			[
				__('Reset Root Password'),
				'reset_root_password',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Enable Performance Schema'),
				'enable_performance_schema',
				true,
				frm.doc.is_server_setup && !frm.doc.is_performance_schema_enabled,
			],
			[
				__('Disable Performance Schema'),
				'disable_performance_schema',
				true,
				frm.doc.is_server_setup && frm.doc.is_performance_schema_enabled,
			],
			[__('Restart MariaDB'), 'restart_mariadb', true, frm.doc.is_server_setup],
			[__('Stop MariaDB'), 'stop_mariadb', true, frm.doc.is_server_setup],
			[
				__('Run Upgrade MariaDB Job'),
				'run_upgrade_mariadb_job',
				true,
				frm.doc.is_server_setup,
			],
			[__('Upgrade MariaDB'), 'upgrade_mariadb', true, frm.doc.is_server_setup],
			[
				__('Upgrade MariaDB Patched'),
				'upgrade_mariadb_patched',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Reconfigure MariaDB Exporter'),
				'reconfigure_mariadb_exporter',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Setup Deadlock Logger'),
				'setup_deadlock_logger',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Setup Percona Stalk'),
				'setup_pt_stalk',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Fetch MariaDB Stalks'),
				'fetch_stalks',
				true,
				frm.doc.is_server_setup && frm.doc.is_stalk_setup,
			],
			[
				__('Fetch Keys'),
				'fetch_keys',
				false,
				frm.doc.is_server_setup &&
					(!frm.doc.frappe_public_key || !frm.doc.root_public_key),
			],
			[__('Update TLS Certificate'), 'update_tls_certificate', true],
			[
				__('Adjust Memory Config'),
				'adjust_memory_config',
				true,
				frm.doc.status === 'Active',
			],
			[__('Create Image'), 'create_image', true, frm.doc.status == 'Active'],
			[__('Archive'), 'archive', true, frm.doc.status !== 'Archived'],
			[
				__('Reboot with serial console'),
				'reboot_with_serial_console',
				true,
				frm.doc.virtual_machine,
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
		if (frm.doc.is_server_setup) {
			frm.add_custom_button(
				__('Increase Swap'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Increase Swap'),
						fields: [
							{
								fieldtype: 'Int',
								label: __('Swap Size'),
								description: __('Size in GB'),
								fieldname: 'swap_size',
								default: 4,
							},
						],
					});

					dialog.set_primary_action(__('Increase Swap'), (args) => {
						frm.call('increase_swap', args).then(() => {
							dialog.hide();
							frm.refresh();
						});
					});
					dialog.show();
				},
				__('Actions'),
			);
		}
	},

	hostname: function (frm) {
		press.set_hostname_abbreviation(frm);
	},
});
