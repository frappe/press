// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Scheduled Deploy Group', {
	deploy_now(frm, cdt, cdn) {
		const release_group = locals[cdt][cdn].release_group
		if (!release_group) return

		frappe.confirm(__('Deploy {0} now?', [release_group]), () =>
			frm.call('deploy_now', { release_group }).then(({ message: build }) =>
				frappe.show_alert({
					message: build
						? __('Deploy of {0} started: {1}', [release_group, build])
						: __('{0} has no app updates to deploy', [release_group]),
					indicator: build ? 'green' : 'orange',
				}),
			),
		)
	},
})
