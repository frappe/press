// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Proxy Server', {
	refresh: function (frm) {
		[
			[__('Ping Agent'), 'ping_agent', false, frm.doc.is_server_setup],
			[__('Ping Ansible'), 'ping_ansible', true],
			[__('Ping Ansible Unprepared'), 'ping_ansible_unprepared', true],
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
			[__('Prepare Server'), 'prepare_server', true, !frm.doc.is_server_setup],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[
				__('Get AWS Static IP'),
				'get_aws_static_ip',
				false,
				frm.doc.provider === 'AWS EC2',
			],
			[
				__('Setup SSH Proxy'),
				'setup_ssh_proxy',
				true,
				frm.doc.ssh_certificate_authority && !frm.doc.is_ssh_proxy_setup,
			],
			[
				__('Setup ProxySQL'),
				'setup_proxysql',
				true,
				!frm.doc.is_proxysql_setup,
			],
			[
				__('Setup ProxySQL Monitor'),
				'setup_proxysql_monitor',
				true,
				frm.doc.is_proxysql_setup,
			],
			[
				__('Setup Wildcard Hosts'),
				'setup_wildcard_hosts',
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
				__('Fetch Keys'),
				'fetch_keys',
				false,
				frm.doc.is_server_setup &&
					(!frm.doc.frappe_public_key || !frm.doc.root_public_key),
			],
			[__('Update TLS Certificate'), 'update_tls_certificate', true],
			[__('Reload NGINX'), 'reload_nginx', true, frm.doc.is_server_setup],
			[__('Create Image'), 'create_image', true, frm.doc.status == 'Active'],
			[
				__('Setup Replication'),
				'setup_replication',
				true,
				frm.doc.is_server_setup &&
					!frm.doc.is_primary &&
					!frm.doc.is_replication_setup,
			],
			[
				__('Execute Pre Failover Tasks'),
				'pre_failover_tasks',
				true,
				frm.doc.is_server_setup && !frm.doc.is_primary,
			],
			[
				__('Trigger Failover'),
				'trigger_failover',
				true,
				frm.doc.is_server_setup &&
					!frm.doc.is_primary &&
					frm.doc.is_replication_setup,
			],
			[__('Archive'), 'archive', true, frm.doc.status !== 'Archived'],
			[__('Setup Fail2ban'), 'setup_fail2ban', true, frm.doc.is_server_setup],
			[__('Remove Fail2ban'), 'remove_fail2ban', true, frm.doc.is_server_setup],
			[__('Setup Wireguard'), 'setup_wireguard', true],
			[__('Reload Wireguard'), 'reload_wireguard', true],
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
				__('Update Memory Limits'),
				() => {
					let process_options = ['', 'nginx', 'filebeat'];
					frm.doc.is_proxysql_setup && process_options.push('proxysql');
					frm.doc.is_ssh_proxy_setup && process_options.push('ssh');

					const dialog = new frappe.ui.Dialog({
						title: 'Set Memory Limits',
						fields: [
							{
								fieldname: 'process_table',
								fieldtype: 'Table',
								label: 'Processes',
								reqd: 1,
								description: 'Use -1 for unsetting limits',
								in_place_edit: true,
								data: [],
								fields: [
									{
										fieldname: 'process',
										fieldtype: 'Select',
										label: 'Process',
										in_list_view: 1,
										columns: 4,
										options: process_options.join('\n'),
										reqd: 1,
									},
									{
										fieldname: 'memory_high',
										fieldtype: 'Int',
										label: 'Memory High (MB)',
										in_list_view: 1,
										reqd: 1,
										columns: 3,
									},
									{
										fieldname: 'memory_max',
										fieldtype: 'Int',
										label: 'Memory Max (MB)',
										in_list_view: 1,
										reqd: 1,
										columns: 5,
									},
								],
							},
						],
						primary_action_label: 'Update',
						primary_action(values) {
							frm
								.call('set_memory_limits', { limits: values.process_table })
								.then((r) => {
									frappe.show_alert(r.message);
									dialog.hide();
								});
						},
					});
					dialog.show();

					frm.call('get_memory_limits').then((r) => {
						if (r.message) {
							r.message.forEach((limit) => {
								dialog.fields_dict.process_table.df.data.push({
									process: limit.process,
									memory_high: limit.memory_high,
									memory_max: limit.memory_max,
								});
							});
						}
						dialog.fields_dict.process_table.grid.refresh();
					});
				},
				__('Actions'),
			);
		}
	},

	hostname: function (frm) {
		press.set_hostname_abbreviation(frm);
	},
});
