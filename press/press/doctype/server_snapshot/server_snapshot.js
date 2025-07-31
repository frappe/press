// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server Snapshot', {
	refresh(frm) {
		[
			[__('Sync'), 'sync', false, true],
			[
				__('Delete'),
				'delete_snapshots',
				true,
				['Pending', 'Completed'].includes(frm.doc.status),
			],
			[__('Unlock'), 'unlock', true, frm.doc.locked],
			[__('Lock'), 'lock', true, !frm.doc.locked],
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
