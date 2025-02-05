// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('SQL Job', {
	refresh(frm) {
		[
			[__('Start'), 'start', frm.doc.status === 'Pending', true],
			[__('Cancel'), 'cancel', frm.doc.status === 'Running', true],
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
