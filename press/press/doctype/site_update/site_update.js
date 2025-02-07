// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Update', {
	onload: function (frm) {
		frm.set_query('destination_bench', function () {
			return {
				filters: {
					status: 'Active',
					server: frm.doc.server,
				},
			};
		});
	},

	refresh: function (frm) {
		// Disable save button
		frm.disable_save();

		// Add link
		frm.add_web_link(
			`/dashboard/sites/${frm.doc.site}/updates/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		// Add custom buttons
		[
			[
				__('Trigger Recovery Job'),
				'trigger_recovery_job',
				!frm.doc.recover_job,
			],
			[__('Start'), 'start', ['Scheduled', 'Failure'].includes(frm.doc.status)],
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
	},
});
