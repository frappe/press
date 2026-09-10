// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Database Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard'),
		)

		;[
			[
				__('Ping Agent'),
				'ping_agent',
				false,
				frm.doc.is_server_setup,
				__('Ping'),
			],
			[
				__('Ping Ansible'),
				'ping_ansible',
				true,
				frm.doc.is_server_prepared,
				__('Ping'),
			],
			[
				__('Ping Ansible Unprepared'),
				'ping_ansible_unprepared',
				true,
				!frm.doc.is_server_prepared,
				__('Ping'),
			],
			[
				__('Update Agent'),
				'update_agent',
				true,
				frm.doc.is_server_setup,
				__('Agent'),
			],
			[
				__('Update Agent Ansible'),
				'update_agent_ansible',
				true,
				frm.doc.is_server_setup,
				__('Agent'),
			],
			[
				__('Install Wazuh Agent'),
				'install_wazuh_agent',
				true,
				frm.doc.is_server_setup,
				__('Setup'),
			],
			[
				__('Uninstall Wazuh Agent'),
				'uninstall_wazuh_agent',
				true,
				frm.doc.is_server_setup && frm.doc.is_wazuh_agent_installed,
				__('Setup'),
			],
			[
				__('Setup Auditd'),
				'setup_auditd',
				true,
				frm.doc.is_server_setup,
				__('Setup'),
			],
			[
				__('Set Additional Config'),
				'set_additional_config',
				true,
				frm.doc.is_server_setup,
				__('Setup'),
			],
			[
				__('Fetch Keys'),
				'fetch_keys',
				true,
				frm.doc.is_server_setup &&
					(!frm.doc.frappe_public_key || !frm.doc.root_public_key),
				__('Setup'),
			],
			[
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
				__('Setup'),
			],
			[
				__('Setup Server'),
				'setup_server',
				true,
				!frm.doc.is_server_setup,
				__('Setup'),
			],
			[
				__('Update DNS Record'),
				'create_dns_record',
				true,
				undefined,
				__('Network'),
			],
			[
				__('Setup Rename'),
				'rename_server',
				true,
				frm.doc.is_server_setup &&
					frm.doc.is_server_prepared &&
					!frm.doc.is_server_renamed,
				__('Setup'),
			],
			[
				__('Convert From Frappe Server'),
				'convert_from_frappe_server',
				true,
				frm.doc.is_server_setup,
				__('Setup'),
			],
			[
				__('Setup Replication'),
				'setup_replication',
				true,
				frm.doc.is_server_setup &&
					!frm.doc.is_primary &&
					!frm.doc.is_replication_setup,
				__('Replication'),
			],
			[
				__('Trigger Failover'),
				'trigger_failover',
				true,
				frm.doc.is_server_setup &&
					!frm.doc.is_primary &&
					frm.doc.is_replication_setup,
				__('Replication'),
			],
			[
				__('Reset Root Password'),
				'reset_root_password',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Enable Performance Schema'),
				'enable_performance_schema',
				true,
				frm.doc.is_server_setup && !frm.doc.is_performance_schema_enabled,
				__('MariaDB'),
			],
			[
				__('Disable Performance Schema'),
				'disable_performance_schema',
				true,
				frm.doc.is_server_setup && frm.doc.is_performance_schema_enabled,
				__('MariaDB'),
			],
			[
				__('Toggle Read-Only Mode'),
				'toggle_read_only_mode',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Restart MariaDB'),
				'restart_mariadb',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Stop MariaDB'),
				'stop_mariadb',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Run Upgrade MariaDB Job'),
				'run_upgrade_mariadb_job',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Update MariaDB'),
				'update_mariadb',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Upgrade MariaDB Patched'),
				'upgrade_mariadb_patched',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Reconfigure MariaDB Exporter'),
				'reconfigure_mariadb_exporter',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Setup Deadlock Logger'),
				'setup_deadlock_logger',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Setup Percona Stalk'),
				'setup_pt_stalk',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Fetch MariaDB Stalks'),
				'fetch_stalks',
				true,
				frm.doc.is_server_setup && frm.doc.is_stalk_setup,
				__('MariaDB'),
			],
			[
				__('Update TLS Certificate'),
				'update_tls_certificate',
				true,
				undefined,
				__('Network'),
			],
			[
				__('Adjust Memory Config'),
				'adjust_memory_config',
				true,
				frm.doc.status === 'Active',
				__('MariaDB'),
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
				__('Setup'),
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
				__('MariaDB'),
			],
			[
				'Sync Binlogs Info',
				'sync_binlogs_info',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				'Sync Replication Config',
				'sync_replication_config',
				true,
				frm.doc.is_server_setup,
				__('Replication'),
			],
			[
				'Trigger Schema Size Sync',
				'update_database_schema_sizes',
				false,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				'Trigger Flush Tables',
				'flush_tables',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Install NAT iptables'),
				'install_nat_iptables',
				true,
				frm.doc.is_server_setup && frm.doc.nat_server,
				__('Network'),
			],
			[__('Get Static IP'), 'get_static_ip', false, undefined, __('Network')],
			[
				__('Remove NAT iptables'),
				'remove_nat_iptables',
				true,
				frm.doc.is_server_setup && !frm.doc.nat_server,
				__('Network'),
			],
			[
				__('Migrate to Cgroup V2'),
				'migrate_to_cgroup_v2',
				true,
				frm.doc.is_server_setup,
				__('Setup'),
			],
			[
				__('Setup MariaDB Monitor'),
				'setup_mariadb_monitor',
				true,
				frm.doc.is_server_setup,
				__('MariaDB'),
			],
			[
				__('Uninstall MariaDB Monitor'),
				'uninstall_mariadb_monitor',
				true,
				frm.doc.is_server_setup && frm.doc.is_mariadb_monitor_installed,
				__('MariaDB'),
			],
		].forEach(([label, method, confirm, condition, group]) => {
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
											frappe.msgprint(r.message)
										} else {
											frm.refresh()
										}
									}),
							)
						} else {
							frm.call(method).then((r) => {
								if (r.message) {
									frappe.msgprint(r.message)
								} else {
									frm.refresh()
								}
							})
						}
					},
					__(group || 'Actions'),
				)
			}
		})
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
					})

					dialog.set_primary_action(__('Increase Swap'), (args) => {
						frm.call('increase_swap', args).then(() => {
							dialog.hide()
							frm.refresh()
						})
					})
					dialog.show()
				},
				__('Actions'),
			)
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
					})

					dialog.set_primary_action(__('Backup'), (args) => {
						frm.call('perform_physical_backup', args).then(() => {
							dialog.hide()
							frm.refresh()
						})
					})
					dialog.show()
				},
				__('Actions'),
			)
			frm.add_custom_button(
				__('Update Memory Allocator Settings'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Update Memory Allocator Settings'),
						fields: [
							{
								fieldtype: 'Select',
								label: __('Memory Allocator'),
								options: ['System', 'jemalloc', 'TCMalloc'].join('\n'),
								default: frm.doc.memory_allocator || 'System',
								fieldname: 'memory_allocator',
								reqd: 1,
							},
							{
								fieldtype: 'Int',
								label: __('tcmalloc Release Rate'),
								description: __(
									'Applicable only if memory allocator is set to tcmalloc. Value must be between 1 and 10. Default is 1. Higher value means more aggressive release of memory to the OS, which can reduce memory usage but may impact performance.',
								),
								default: frm.doc.tcmalloc_release_rate || 1,
								fieldname: 'tcmalloc_release_rate',
							},
						],
					})

					dialog.set_primary_action(__('Update'), (args) => {
						frm.call({
							method: 'update_memory_allocator',
							doc: frm.doc,
							args: args,
							freeze: true,
							callback: () => {
								dialog.hide()
								frm.refresh()
							},
						})
					})
					dialog.show()
				},
				__('Dangerous Actions'),
			)

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
					})

					dialog.set_primary_action(__('Purge'), (args) => {
						frm.call({
							method: 'purge_binlogs',
							doc: frm.doc,
							args: args,
							freeze: true,
							callback: () => {
								dialog.hide()
								frm.refresh()
							},
						})
					})
					dialog.show()
				},
				__('Dangerous Actions'),
			)
		}
	},

	hostname: function (frm) {
		press.set_hostname_abbreviation(frm)
	},
})
