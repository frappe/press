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
		} else if (frm.doc.status === 'Scheduled') {
			frm.add_custom_button(__('Start'), () => {
				frappe.confirm(
					`Are you sure you want to start the migration?<br>

					<b>Note: This will start downtime</b>`,
					() => frm.call('start'),
				);
			});
		} else if (frm.doc.status === 'Running') {
			frm.add_custom_button(__('Fail'), () => {
				frappe.confirm(
					`Are you sure you want to stop and fail the migration?<br>

					This will attempt to stop the migration and put everything back to the original state.<br>

					<b>Note: This could cause data loss if you don't know what you're doing</b>`,
					() => frm.call('fail'),
				);
			});
		}
	},
});
