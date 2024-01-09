// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agent Job', {
	refresh: function (frm) {
		frm.add_web_link(
			`https://${frm.doc.server}/agent/jobs/${frm.doc.job_id}`,
			__('Visit Agent Endpoint'),
		);

		if (!['Success', 'Failure', 'Delivery Failure'].includes(frm.doc.status)) {
			frm.add_custom_button(
				__('Get Status'),
				() => {
					frm.call('get_status').then(() => frm.refresh());
				},
				__('Actions'),
			);
		}

		frm.add_custom_button(
			__('Retry'),
			() => {
				frappe.confirm(`Are you sure you want to retry this job?`, () =>
					frm
						.call('retry')
						.then((result) =>
							frappe.msgprint(
								frappe.utils.get_form_link(
									'Agent Job',
									result.message.name,
									true,
								),
							),
						),
				);
			},
			__('Actions'),
		);

		[
			[__('Retry In-Place'), 'retry_in_place'],
			[__('Process Job Updates'), 'process_job_updates'],
			[__('Fail and Process Job Updates'), 'fail_and_process_job_updates'],
			[
				__('Succeed and Process Job Updates'),
				'succeed_and_process_job_updates',
			],
		].forEach(([label, method, condition]) => {
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
		});
		if (['Update Site Migrate', 'Migrate Site'].includes(frm.doc.job_type)) {
			frm.add_custom_button(
				'Run by Skipping Failing Patches',
				() => {
					frm
						.call('retry_skip_failing_patches')
						.then((result) =>
							frappe.msgprint(
								frappe.utils.get_form_link(
									'Agent Job',
									result.message.name,
									true,
								),
							),
						);
				},
				__('Actions'),
			);
		}
	},
});
