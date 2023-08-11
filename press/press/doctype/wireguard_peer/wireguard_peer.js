// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wireguard Peer', {
	refresh: function (frm) {
		[
			[__('Setup Wireguard'), 'setup_wireguard', false],
			[__('Ping Peer'), 'ping_peer', false],
			[__('Fetch Private Network'), 'fetch_peer_private_network', false],
			[__('Generate Config'), 'generate_config', false],
			[__('Generate QR'), 'generate_qr_code', false],
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
