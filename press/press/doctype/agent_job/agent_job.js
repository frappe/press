// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agent Job', {
	refresh: function (frm) {
		frm.add_web_link(
			`https://${frm.doc.server}/agent/jobs/${frm.doc.job_id}`,
			__('Visit Agent Endpoint')
		);

		frm.add_custom_button(__('Retry'), () => {
			frappe.confirm(`Are you sure you want to retry this job?`, () =>
				frm
					.call('retry')
					.then((result) =>
						frappe.msgprint(
							frappe.utils.get_form_link('Agent Job', result.message.name, true)
						)
					)
			);
		});

		if (['Update Site Migrate', 'Migrate Site'].includes(frm.doc.job_type)) {
			frm.add_custom_button('Run by Skipping Failing Patches', () => {
				frm
					.call('retry_skip_failing_patches')
					.then((result) =>
						frappe.msgprint(
							frappe.utils.get_form_link('Agent Job', result.message.name, true)
						)
					);
			});
		}
	},
});
