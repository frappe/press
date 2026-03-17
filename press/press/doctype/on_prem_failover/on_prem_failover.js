// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('On-Prem Failover', {
	refresh(frm) {
		[
			[
				'View On-Prem Wireguard Config',
				'view_on_prem_server_wireguard_config',
				false,
				true,
			],
			[
				'Setup On-Prem Failover',
				'setup_failover',
				true,
				!frm.doc.is_app_server_failover_setup ||
					!frm.doc.is_db_server_failover_setup,
			],
			[
				'Teardown On-Prem Failover',
				'teardown_failover',
				true,
				frm.doc.is_app_server_failover_setup &&
					frm.doc.is_db_server_failover_setup,
			],
			[
				'View On-Prem SSH Authorized Keys',
				'view_on_prem_server_ssh_authorized_keys',
				false,
				true,
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
