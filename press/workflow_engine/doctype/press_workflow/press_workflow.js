// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Press Workflow', {
	refresh(frm) {
		if (frm.doc.status === 'Running') {
			frm.add_custom_button(
				'Force Fail',
				() => {
					frappe.confirm(
						'Are you sure you want to force fail this workflow? This action cannot be undone.',
						() => {
							frm.call('force_fail').then(() => {
								frm.reload_doc();
							});
						},
					);
				},
				'Actions',
			);
		}
	},
});
