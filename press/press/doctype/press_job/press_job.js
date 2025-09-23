// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Press Job', {
	refresh: function (frm) {
		[
			[__('Force Continue'), 'force_continue', frm.doc.status === 'Failure'],
			[__('Force Fail'), 'force_fail', frm.doc.status === 'Running'],
			[
				__('Mark Callback Failure Issue Resolved'),
				'mark_callback_failure_issue_resolved',
				frm.doc.callback_failed &&
					!frm.doc.callback_executed &&
					!frm.doc.callback_failure_issue_resolved,
			],
		].forEach(([label, method, condition]) => {
			if (condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()}?`,
							() => frm.call(method).then(() => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});
	},
});
