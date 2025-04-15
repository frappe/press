// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt
frappe.ui.form.on('Deploy Candidate Build', {
	refresh(frm) {
		frm.add_web_link(
			`/dashboard/groups/${frm.doc.group}/deploys/${frm.doc.name}`,
			__('Visit Dashboard'),
		);
		[
			[
				__('Cleanup Directory'),
				'cleanup_build_directory',
				typeof frm.doc.build_directory !== 'undefined' &&
					frm.doc.status !== 'Running',
			],
			[
				__('Stop And Fail'),
				null,
				!['Success', 'Failure'].includes(frm.doc.status),
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(label, () => {
					if (label === 'Stop And Fail') {
						frappe.call('press.api.deploy_candidate_build.stop_and_fail', {
							dn: frm.doc.name,
						});
					}
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
