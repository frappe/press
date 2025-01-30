// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physical Backup Restoration', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		[
			[__('Start'), 'execute', frm.doc.status === 'Pending', false],
			[__('Force Continue'), 'force_continue', true],
			[__('Cleanup'), 'cleanup', frm.doc.status === 'Failure', true],
			[__('Force Fail'), 'force_fail', frm.doc.status === 'Running', false],
		].forEach(([label, method, condition, grouped]) => {
			if (condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()}?`,
							() => frm.call(method).then(() => frm.refresh()),
						);
					},
					grouped ? __('Actions') : null,
				);
			}
		});
	},
});
