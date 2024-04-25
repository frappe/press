// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Source', {
	refresh(frm) {
		async function create_release() {
			await frm.call('create_release', { force: true });
			frm.refresh();
		}
		frm.add_custom_button(__('Create Release'), create_release, __('Actions'));
	},
});
