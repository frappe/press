// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Self Hosted Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard'),
		);
		[
			[__('Ping Server'), 'ping_ansible', false],
			[__('Fetch Ram'), 'fetch_system_ram', false, !frm.doc.ram],
			[__('Setup Nginx'), '_setup_nginx', false],
			[__('Update TLS'), 'update_tls', false],
			[__('Create Proxy Server'), 'create_proxy_server', false],
			[
				__('Create Database Server'),
				'create_db_server',
				false,
				frm.doc.proxy_created,
			],
			[__('Create App Server'), 'create_server', false, frm.doc.database_setup],
			[
				__('Restore Files from Existing Sites'),
				'restore_files',
				true,
				frm.doc.existing_bench_present,
			],
			[
				__('Get Apps from Existing Bench'),
				'fetch_apps_and_sites',
				false,
				frm.doc.existing_bench_present,
			],
			[
				__('Create a Release Group for Existing Bench'),
				'create_new_rg',
				false,
				frm.doc.existing_bench_present,
			],
			[
				__('Create Sites from Existing Bench'),
				'create_new_sites',
				true,
				frm.doc.existing_bench_present && frm.doc.release_group,
			],
			,
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
	onload: (frm) => {
		frm.set_query('server', () => {
			return {
				filters: {
					is_self_hosted: true,
				},
			};
		});
	},
});
