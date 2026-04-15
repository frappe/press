// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB Upgrade', {
	refresh(frm) {
		if (frm.doc.status == 'Pending') {
			frm.add_custom_button(
				'Start Upgrade',
				() => {
					frappe.confirm(
						'Are you sure you want to start the MariaDB Upgrade? Please ensure that you have taken a backup of your data before proceeding.',
						() => {
							frm.call('start').then(() => {
								frappe.msgprint(
									'MariaDB Upgrade has been started. Please check the workflow for progress.',
								);
							});
						},
					);
				},
				__('Actions'),
			);
		}

		if (
			['Success', 'Recovered', 'Fatal'].includes(frm.doc.status) &&
			frm.doc.snapshot
		) {
			frm.add_custom_button(
				'Delete Snapshot',
				() => {
					frappe.confirm(
						'Are you sure you want to delete the snapshot? This action cannot be undone.',
						() => {
							frm.call('delete_snapshot').then(() => {
								frappe.msgprint('Snapshot has been deleted successfully.');
								frm.refresh();
							});
						},
					);
				},
				__('Actions'),
			);
		}
	},
});
