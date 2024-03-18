// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Patch', {
	refresh(frm) {
		const custom_buttons = [
			[__('Apply Patch'), 'apply_patch', frm.doc.status !== 'In Process'],
			[__('Revert Patch'), 'revert_patch', frm.doc.status !== 'In Process'],
			// [__('Revert All Patches'), 'revert_all_patches', true],
		];

		for (const [label, method, show] of custom_buttons) {
			if (!show) {
				continue;
			}

			const handler = () =>
				frm
					.call(method)
					.then((_) => frm.refresh())
					.catch((_) => frm.refresh());
			frm.add_custom_button(label, handler, __('Actions'));
		}
	},
});
