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
		if (['Scheduled', 'Failure'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Continue'), () => {
				frappe.confirm(
					`Are you sure you want to continue from next Pending step?

					<b>Note: This could cause data loss if you don't know what you're doing</b>`,
					() => frm.call('continue_from_next_pending'),
				);
			});
		}
	},
});
