// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Scheduled Deploy Group', {
	deploy_now(frm, cdt, cdn) {
		const release_group = locals[cdt][cdn].release_group
		if (!release_group) return

		frappe.confirm(__('Deploy {0} now?', [release_group]), () =>
			frm.call('deploy_now', { release_group }).then(() =>
				frappe.show_alert({
					message: __(
						'Deploy of {0} queued. A new Deploy Candidate shows up once it starts, or an Error Log if a check stops it.',
						[release_group],
					),
					indicator: 'blue',
				}),
			),
		)
	},
})
