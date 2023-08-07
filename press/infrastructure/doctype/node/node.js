// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Node', {
	refresh: function (frm) {
		[
			[__('Ping Agent'), 'ping_agent', false, frm.doc.is_server_setup],
			[__('Ping Ansible'), 'ping_ansible', true, !frm.doc.is_server_prepared],
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
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Setup'), 'setup', true, !frm.doc.is_server_setup],
			[
				__('Show Agent Password'),
				'show_agent_password',
				false,
				frm.doc.is_server_setup,
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
