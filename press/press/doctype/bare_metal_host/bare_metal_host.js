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

async function frappe_confirm(label) {
	return new Promise((r) => {
		frappe.confirm(
			`Are you sure you want to ${label.toLowerCase()}?`,
			() => r(true),
			() => r(false),
		);
	});
} 