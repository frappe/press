// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Scheduled Deploy Group', {
	deploy_now(frm, cdt, cdn) {
		const release_group = locals[cdt][cdn].release_group
		if (!release_group) return

		frappe.confirm(__('Deploy {0} now?', [release_group]), () =>
			frm.call('deploy_now', { release_group }).then(({ message }) => {
				const job_link = frappe.utils.get_form_link(
					'RQ Job',
					message.job,
					true,
					__('View the job'),
				)
				frappe.msgprint({
					title: message.already_queued
						? __('Deploy already queued')
						: __('Deploy queued'),
					indicator: message.already_queued ? 'orange' : 'blue',
					message: message.already_queued
						? __(
								'A deploy of {0} is already queued or running, so no new one was added. {1}',
								[release_group, job_link],
							)
						: __(
								'Deploy of {0} queued. A new Deploy Candidate shows up once it starts, or an Error Log entry if a check stops it. {1}',
								[release_group, job_link],
							),
				})
			}),
		)
	},
})
