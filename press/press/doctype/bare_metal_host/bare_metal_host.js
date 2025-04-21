// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bare Metal Host', {
	refresh: function(frm) {
		frm.add_web_link(
			`/dashboard/bare-metal-hosts/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		const ping_actions = [
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
				if (res.message) {
					frappe.msgprint(res.message);
				} else {
					frm.refresh();
				}
			}

			frm.add_custom_button(label, callback, __('Ping'));
		}

		[
			[
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[__('Install Nginx'), 'install_nginx', true, frm.doc.is_server_prepared && !frm.doc.is_server_setup],
			[__('Install Filebeat'), 'install_filebeat', true, frm.doc.is_server_setup],
			[__('Setup VM Host'), 'setup_vm_host', true, frm.doc.is_server_setup && frm.doc.is_vm_host && !frm.doc.is_vm_host_setup],
			[__('Setup NFS Server'), 'setup_nfs_server', true, frm.doc.is_server_setup && !frm.doc.is_nfs_server],
			[__('Setup VM Host with NFS'), 'setup_vm_host_with_nfs', true, frm.doc.is_server_setup && frm.doc.is_vm_host && !frm.doc.is_vm_host_setup],
			[__('Optimize NFS Server'), 'optimize_nfs_server', true, frm.doc.is_server_setup && frm.doc.is_nfs_server],
			[__('Check NFS Connectivity'), 'check_nfs_connectivity', true, frm.doc.is_server_setup],
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

		// Add NFS status indicators
		frm.dashboard.add_indicator(__("NFS Server: {0}", [__(frm.doc.is_nfs_server ? "Yes" : "No")]), frm.doc.is_nfs_server ? "green" : "gray");
		frm.dashboard.add_indicator(__("NFS Client: {0}", [__(frm.doc.is_nfs_client ? "Yes" : "No")]), frm.doc.is_nfs_client ? "green" : "gray");
	},

	setup: function(frm) {
		frm.set_query("monitoring_server", function() {
			return {
				filters: {
					server_type: "Monitoring"
				}
			};
		});
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