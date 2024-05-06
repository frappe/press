// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mirror Server', {
	refresh(frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		[
			[
				__('Prepare Server'),
				'prepare_server',
				true,
				!frm.doc.is_server_prepared,
			],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
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
