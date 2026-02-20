// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Database Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		[
			[__('Ping Agent'), 'ping_agent', false, frm.doc.is_server_setup],
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
				__('Install Filebeat'),
				'install_filebeat',
				true,
				frm.doc.is_server_setup,
			],
			[__('Setup Logrotate'), 'setup_logrotate', true, frm.doc.is_server_setup],
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
			[
				__('Toggle Read-Only Mode'),
				'toggle_read_only_mode',
				true,
				frm.doc.is_server_setup,
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
			[__('Update MariaDB'), 'update_mariadb', true, frm.doc.is_server_setup],
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
			[
				__('Setup Essentials'),
				'setup_essentials',
				true,
				frm.doc.is_self_hosted,
			],
			[
				__('Mount Volumes'),
				'mount_volumes',
				true,
				frm.doc.virtual_machine && frm.doc.mounts,
			],
			[
				'Get Binlog Summary',
				'get_binlog_summary',
				true,
				frm.doc.is_server_setup,
			],
			['Sync Binlogs Info', 'sync_binlogs_info', true, frm.doc.is_server_setup],
			[
				'Sync Replication Config',
				'sync_replication_config',
				true,
				frm.doc.is_server_setup,
			],
			[
				'Provide Frappe User DU and Find Permission',
				'provide_frappe_user_du_and_find_permission',
				true,
				frm.doc.is_server_setup,
			],
			[
				'Trigger Schema Size Sync',
				'update_database_schema_sizes',
				false,
				frm.doc.is_server_setup,
			],
			['Trigger Flush Tables', 'flush_tables', true, frm.doc.is_server_setup],
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
			frm.add_custom_button(
				__('Perform Physical Backup'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Perform Physical Backup'),
						fields: [
							{
								fieldtype: 'Data',
								label: __('Backup Path'),
								description: __('Absolute path to store the backup'),
								default: '/tmp/replica',
								fieldname: 'path',
								reqd: 1,
							},
						],
					});

					dialog.set_primary_action(__('Backup'), (args) => {
						frm.call('perform_physical_backup', args).then(() => {
							dialog.hide();
							frm.refresh();
						});
					});
					dialog.show();
				},
				__('Actions'),
			);
			frm.add_custom_button(
				__('Update Memory Allocator'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Update Memory Allocator'),
						fields: [
							{
								fieldtype: 'Select',
								label: __('Memory Allocator'),
								options: ['System', 'jemalloc', 'TCMalloc']
									.filter((option) => option !== frm.doc.memory_allocator)
									.join('\n'),
								fieldname: 'memory_allocator',
								reqd: 1,
							},
						],
					});

					dialog.set_primary_action(__('Update'), (args) => {
						frm.call({
							method: 'update_memory_allocator',
							doc: frm.doc,
							args: args,
							freeze: true,
							callback: () => {
								dialog.hide();
								frm.refresh();
							},
						});
					});
					dialog.show();
				},
				__('Dangerous Actions'),
			);

			frm.add_custom_button(
				__('Purge Binlogs'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Purge Binlogs'),
						fields: [
							{
								fieldtype: 'Data',
								label: __('To Binlog (mysql-bin.xxxxxx)'),
								fieldname: 'to_binlog',
								reqd: 1,
							},
						],
					});

					dialog.set_primary_action(__('Purge'), (args) => {
						frm.call({
							method: 'purge_binlogs',
							doc: frm.doc,
							args: args,
							freeze: true,
							callback: () => {
								dialog.hide();
								frm.refresh();
							},
						});
					});
					dialog.show();
				},
				__('Dangerous Actions'),
			);
		}
	},

	hostname: function (frm) {
		press.set_hostname_abbreviation(frm);
	},
});
