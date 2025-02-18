// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physical Restoration Test', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		[
			[__('Start / Resume'), 'start', false],
			[__('Sync'), 'sync', false],
		].forEach(([label, method, grouped]) => {
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
		});
	},
});
