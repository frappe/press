// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Migration', {
	refresh: function (frm) {
		frm.set_query('site', () => {
			return {
				filters: {
					status: 'Active',
				},
			};
		});
		frm.set_query('source_bench', () => {
			return {
				filters: {
					status: 'Active',
				},
			};
		});
		frm.set_query('destination_bench', () => {
			return {
				filters: {
					status: 'Active',
				},
			};
		});
		if (frm.doc.status === 'Failure') {
			frm.add_custom_button(__('Continue'), () => {
				frappe.confirm(
					`Are you sure you want to continue from next Pending step?<br>

					<b>Note: This could cause data loss if you don't know what you're doing</b>`,
					() => frm.call('continue_from_next_pending'),
				);
			});
			frm.add_custom_button(__('Set Skipped to Pending'), () => {
				frappe.confirm(
					`Are you sure you want to set all Skipped steps to Pending?<br>

					<b>Note: This could cause data loss if you don't know what you're doing</b>`,
					() => {
						frm.set_value(
							'steps',
							frm.doc.steps.map((step) => {
								if (step.status === 'Skipped') {
									step.status = 'Pending';
								}
								return step;
							}),
						);
						frm.save();
					},
				);
			});
		} else if (frm.doc.status === 'Scheduled') {
			frm.add_custom_button(__('Start'), () => {
				frappe.confirm(
					`Are you sure you want to start the migration?<br>

					<b>Note: This will start downtime</b>`,
					() => frm.call('start'),
				);
			});
		} else if (frm.doc.status === 'Running') {
			frm.add_custom_button(__('Cleanup and fail'), () => {
				frappe.confirm(
					`Are you sure you want to skip pending steps and fail the migration?<br>

					This will attempt to stop the migration and put everything back to the original state.<br>

					<b>Note: This could cause data loss if you don't know what you're doing</b>`,
					() => frm.call('cleanup_and_fail'),
				);
			});
		}
		if (frm.is_new()) {
			frm.dashboard.set_headline_alert(
				__(
					`Scheduled time not set. The migration will start immediately on save`,
				),
				'orange',
			);
		}
	},
	scheduled_time: function (frm) {
		if (frm.doc.scheduled_time) {
			frm.dashboard.clear_headline();
		}
	},
});
