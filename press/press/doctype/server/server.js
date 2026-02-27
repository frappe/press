// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		const ping_actions = [
			[__('Ping Agent'), 'ping_agent', false, frm.doc.is_server_setup],
			[
				__('Ping Agent (Job)'),
				'ping_agent_job',
				false,
				frm.doc.is_server_setup,
			],
			[__('Ping Ansible'), 'ping_ansible', true, !frm.doc.is_server_prepared],
			[
				__('Ping Ansible Unprepared'),
				'ping_ansible_unprepared',
				true,
				!frm.doc.is_server_prepared,
			],
		];

		for (const [label, method, confirm, condition] of ping_actions) {
			if (!condition || typeof condition === 'undefined') {
				continue;
			}

			async function callback() {
				if (confirm && !(await frappe_confirm(label))) {
					return;
				}

				const res = await frm.call(method);
				if (res.message && method == 'ping_agent_job') {
					frappe.msgprint(
						`Agejt Job <a href="/app/agent-job/${res?.message}">${res?.message}</a> created.`,
					);
				} else if (res.message) {
					frappe.msgprint(res.message);
				} else {
					frm.refresh();
				}
			}

			frm.add_custom_button(label, callback, __('Ping'));
		}

		[
			[__('Update Agent'), 'update_agent', true, frm.doc.is_server_setup],
			[
				__('Install Filebeat'),
				'install_filebeat',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Update Agent Ansible'),
				'update_agent_ansible',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Get AWS Static IP'),
				'get_aws_static_ip',
				false,
				frm.doc.provider === 'AWS EC2',
			],
			[__('Setup Logrotate'), 'setup_logrotate', true, frm.doc.is_server_setup],
			[
				__('Setup PySpy'),
				'setup_pyspy',
				false,
				frm.doc.is_server_setup && !frm.doc.is_pyspy_setup,
			],
			[
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[
				__('Setup Unified Server'),
				'setup_unified_server',
				true,
				frm.doc.is_unified_server,
			],
			[
				__('Add to Proxy'),
				'add_upstream_to_proxy',
				true,
				frm.doc.is_server_setup && !frm.doc.is_upstream_setup,
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
				__('Setup Rename'),
				'rename_server',
				true,
				frm.doc.is_server_setup &&
					frm.doc.is_server_prepared &&
					!frm.doc.is_server_renamed,
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
				__('Auto Scale Workers'),
				'auto_scale_workers',
				true,
				frm.doc.status == 'Active' &&
					frm.doc.is_primary &&
					frm.doc.is_server_setup,
			],
			[
				__('Cleanup Unused Files'),
				'cleanup_unused_files',
				true,
				frm.doc.status == 'Active' && frm.doc.is_server_setup,
			],
			[__('Create Image'), 'create_image', true, frm.doc.status == 'Active'],
			[__('Archive'), 'archive', true, frm.doc.status !== 'Archived'],
			[
				__('Setup MySQLdump'),
				'setup_mysqldump',
				true,
				frm.doc.is_server_setup && frm.doc.status == 'Active',
			],
			[
				__('Whitelist Server'),
				'whitelist_ipaddress',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Agent Setup Proxy IP'),
				'agent_set_proxy_ip',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Setup Agent Sentry'),
				'setup_agent_sentry',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Start Active Benches'),
				'start_active_benches',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Show Agent Password'),
				'show_agent_password',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Show Agent Version'),
				'show_agent_version',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Setup Standalone'),
				'setup_standalone',
				false,
				frm.doc.is_server_setup &&
					frm.doc.is_standalone &&
					!frm.doc.is_standalone_setup,
			],
			[
				__('Fetch Security Updates'),
				'fetch_security_updates',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Configure SSH logging'),
				'configure_ssh_logging',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Reset Usage for all sites'),
				'reset_sites_usage',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Reboot with serial console'),
				'reboot_with_serial_console',
				true,
				frm.doc.provider === 'AWS EC2',
			],
			[
				__('Enable Public Bench and Site Creation'),
				'enable_for_new_benches_and_sites',
				true,
				frm.doc.virtual_machine,
			],
			[
				__('Disable Public Bench and Site Creation'),
				'disable_for_new_benches_and_sites',
				true,
				frm.doc.virtual_machine,
			],
			[
				__('Set Swappiness and SysRq'),
				'set_swappiness',
				false,
				frm.doc.is_server_setup,
			],
			[
				__('Mount Volumes'),
				'mount_volumes',
				true,
				frm.doc.virtual_machine && frm.doc.mounts,
			],
			[
				__('Collect ARM Images'),
				'collect_arm_images',
				true,
				frm.doc.virtual_machine &&
					frm.doc.status === 'Active' &&
					frm.doc.platform === 'x86_64',
			],
			[__('Scale Up'), 'scale_up', true, !frm.doc.scaled_up],
			[__('Scale Down'), 'scale_down', true, frm.doc.scaled_up],
			[__('Setup Firewall'), 'setup_firewall', true, frm.doc.is_server_setup],
			[
				__('Teardown Firewall'),
				'teardown_firewall',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Install Wazuh Agent'),
				'install_wazuh_agent',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Uninstall Wazuh Agent'),
				'uninstall_wazuh_agent',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Setup Wildcard Hosts'),
				'setup_wildcard_hosts',
				true,
				frm.doc.is_server_setup && frm.doc.is_standalone_setup,
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

		if ((frm.doc.is_server_setup, frm.doc.is_primary)) {
			frm.add_custom_button(
				'Setup Secondary Server',
				() => {
					frappe.prompt(
						[
							{
								fieldtype: 'Link',
								fieldname: 'server_plan',
								label: __('Server Plan'),
								options: 'Server Plan',
								reqd: 1,
							},
						],
						({ server_plan }) => {
							frm
								.call('setup_secondary_server', {
									server_plan: server_plan,
								})
								.then((r) => {
									frm.refresh();
								});
						},
					);
				},
				__('Actions'),
			);
		}

		if (frm.doc.is_server_setup) {
			frm.add_custom_button(
				__('Increase Swap'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Increase Swap'),
						fields: [
							{
								fieldtype: 'Int',
								label: __('Swap Size (GB)'),
								description: __('Add additional swap'),
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
				__('Reset Swap'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Swap Size'),
						fields: [
							{
								fieldtype: 'Int',
								label: __('Swap Size (GB)'),
								description: __(
									'This will reset swap space to specified size. 0 or empty to remove all.',
								),
								fieldname: 'swap_size',
								default: 1,
							},
						],
					});

					dialog.set_primary_action(__('Reset Swap'), (args) => {
						frm.call('reset_swap', args).then(() => {
							dialog.hide();
							frm.refresh();
						});
					});
					dialog.show();
				},
				__('Actions'),
			);

			frm.add_custom_button(
				__('Snapshot Both Servers'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Snapshot Both Servers'),
						fields: [
							{
								fieldtype: 'Check',
								label: 'Consistent Snapshot',
								description:
									'This will stop the running services during snapshot creation.',
								fieldname: 'consistent',
								default: 1,
							},
						],
					});

					dialog.set_primary_action(__('Submit'), (args) => {
						frm.call('create_snapshot', args).then(() => {
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

async function frappe_confirm(label) {
	return new Promise((r) => {
		frappe.confirm(
			`Are you sure you want to ${label.toLowerCase()}?`,
			() => r(true),
			() => r(false),
		);
	});
}
