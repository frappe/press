// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agent Update', {
	refresh(frm) {
		[
			[
				__('Build Plan'),
				'create_execution_plan',
				true,
				frm.doc.status === 'Draft',
			],
			[
				__('Start'),
				'execute',
				true,
				frm.doc.status === 'Pending' || frm.doc.status === 'Paused',
			],
			[__('Pause'), 'pause', true, frm.doc.status === 'Running'],
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(label, () => {
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
				});
			}
		});

		if (frm.doc.status === 'Pending') {
			frm.add_custom_button(__('Split Update'), () => {
				const no_of_servers = cur_frm.doc.servers.length;
				const dialog = new frappe.ui.Dialog({
					title: __('Split Updates in Multiple Batches'),

					fields: [
						{
							fieldtype: 'Int',
							label: __('Number of Batches'),
							description: __(
								`Number of batches to split ${no_of_servers} updates`,
							),
							fieldname: 'no_of_batches',
							default: 2,
						},
					],
				});

				dialog.set_primary_action(__('Split'), (args) => {
					frm.call({
						method: 'split_updates',
						doc: frm.doc,
						args: args,
						freeze: true,
						callback: () => {
							dialog.hide();
							frm.refresh();
						},
					});
				});
				dialog.show();
			});
		}
	},
});
