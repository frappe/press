// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate Build', {
	refresh(frm) {
		[
			[
				__('Cleanup Directory'),
				'cleanup_build_directory',
				typeof frm.doc.build_directory !== 'undefined',
			],
			[
				__('Stop And Fail'),
				'stop_and_fail',
				!['Success', 'Failure'].includes(frm.doc.status),
				,
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(label, () => {
					frm.call(method).then((r) => {
						if (r.message.error) {
							frappe.msgprint(__(r.message.message));
						}
					});
				});
			}
		});
	},
});
