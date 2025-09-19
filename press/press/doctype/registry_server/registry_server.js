// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Registry Server', {
	refresh: function (frm) {
		[
			[__('Ping Ansible'), 'ping_ansible', true],
			[__('Ping Ansible Unprepared'), 'ping_ansible_unprepared', true],
			[__('Prepare Server'), 'prepare_server', true, !frm.doc.is_server_setup],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[
				__('Update TLS Certificate'),
				'update_tls_certificate',
				true,
				frm.doc.is_server_setup,
			],
			[
				__('Fetch Keys'),
				'fetch_keys',
				false,
				frm.doc.is_server_setup &&
					(!frm.doc.frappe_public_key || !frm.doc.root_public_key),
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
			if (method == 'create_registry_mirror') {
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt(
							[
								{
									fieldtype: 'Data',
									label: 'Hostname',
									fieldname: 'hostname',
									reqd: 1,
								},
								{
									fieldtype: 'Data',
									label: 'Mount Point',
									fieldname: 'docker_data_mountpoint',
									reqd: 1,
								},
								{
									fieldtype: 'Data',
									label: 'Container Registry Config Path',
									fieldname: 'container_registry_config_path',
									reqd: 1,
								},
								{
									fieldtype: 'Data',
									label: 'Public IP',
									fieldname: 'public_ip',
									reqd: 1,
								},
								{
									fieldtype: 'Data',
									label: 'Private IP',
									fieldname: 'private_ip',
									reqd: 1,
								},
								{
									fieldname: 'Data',
									label: 'Proxy Pass',
									fieldname: 'proxy_pass',
									reqd: 1,
								},
							],
							({
								hostname,
								docker_data_mountpoint,
								container_registry_config_path,
								public_ip,
								private_ip,
								proxy_pass,
							}) => {
								frm
									.call(method, {
										hostname,
										docker_data_mountpoint,
										container_registry_config_path,
										public_ip,
										private_ip,
										proxy_pass,
									})
									.then((r) => frm.refresh());
							},
							__('Create Mirror Registry'),
						);
					},
					__('Actions'),
				);
			}
		});
	},
});
