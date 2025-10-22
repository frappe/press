// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Disk Resize', {
	refresh(frm) {
		[
<<<<<<< HEAD
			[
				__('Start'),
				'execute',
				frm.doc.status === 'Ready' || frm.doc.status === 'Scheduled',
			],
=======
			[__('Start'), 'execute', frm.doc.status === 'Pending'],
>>>>>>> 95eb9555b (fix(virtual-disk-resize): Do not invoke execute resize for undefined scheduled time on insert)
			[__('Force Continue'), 'force_continue', frm.doc.status === 'Failure'],
			[__('Force Fail'), 'force_fail', frm.doc.status === 'Running'],
			[__('Propagate Volume ID'), 'propagate_volume_id'],
		].forEach(([label, method, condition]) => {
			if (condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()}?`,
							() => frm.call(method).then(() => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});
	},
});
