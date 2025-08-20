// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Logical Replication Backup', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		[
			[__('Start'), 'execute', frm.doc.status === 'Pending'],
			[__('Force Continue'), 'force_continue', true],
			[__('Force Fail'), 'force_fail', frm.doc.status === 'Running'],
			[__('Next [Caution]'), 'next', frm.doc.status === 'Failure'],
		].forEach(([label, method, condition]) => {
			if (condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()}?`,
							() =>
								frm
									.call(method, {
										freeze: true,
										freeze_message: __('Please wait...'),
									})
									.then(() => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});
	},
});
