// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate Build', {
	refresh(frm) {
		[[__('Cleanup Directory'), 'cleanup_build_directory']].forEach(
			([label, method, condition]) => {
				frm.add_custom_button(label, () => {
					frm.call(method).then((r) => frm.refresh());
				});
			},
		);
	},
});
