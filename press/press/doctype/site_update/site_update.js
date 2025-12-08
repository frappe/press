// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Update', {
	refresh: function (frm) {
		// Disable save button
		frm.disable_save();

		// Add link
		frm.add_web_link(
			`/dashboard/sites/${frm.doc.site}/updates/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		if (frm.doc.status === 'Cancelled') return;

		// Add custom buttons
		[
			[
				__('Trigger Recovery Job'),
				'trigger_recovery_job',
				!frm.doc.recover_job,
			],
			[__('Start'), 'start', ['Scheduled', 'Failure'].includes(frm.doc.status)],
			[
				__('Cause of Failure is Resolved'),
				'set_cause_of_failure_is_resolved',
				!frm.doc.cause_of_failure_is_resolved,
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()} this site update?`,
							() => frm.call(method).then((r) => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});

		// Allow to change status
		frm.add_custom_button(
			__('Change Status'),
			() => {
				let options = ['Success', 'Recovered', 'Failure', 'Fatal'];
				frm.doc.status === 'Scheduled' ? options.push('Cancelled') : null;

				const dialog = new frappe.ui.Dialog({
					title: __('Change Status'),
					fields: [
						{
							fieldtype: 'Select',
							label: __('Status'),
							fieldname: 'status',
							options: options,
						},
					],
				});

				dialog.set_primary_action(__('Change Status'), (args) => {
					frm
						.call('set_status', {
							status: args.status,
						})
						.then((r) => {
							dialog.hide();
							frm.reload_doc();
						});
				});

				dialog.show();
			},
			__('Actions'),
		);
	},
});
