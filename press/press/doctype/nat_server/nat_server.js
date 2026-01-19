// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('NAT Server', {
	refresh(frm) {
		[
			[__('Prepare Server'), 'prepare_server', true, !frm.doc.is_server_setup],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[__('Archive Server'), 'archive', true, frm.doc.is_server_setup],
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
