// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Container', {
	refresh(frm) {
		[
			[__('Deploy'), 'deploy', frm.doc.status === 'Draft'],
			[__('Archive'), 'archive', frm.doc.status !== 'Archived'],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()} this container?`,
							() => frm.call(method).then((r) => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});
	},
});
