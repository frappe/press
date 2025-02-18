// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physical Backup Experiment Group', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		[
			[__('Sync'), 'sync', false],
			[__('Trigger Next Backup'), 'trigger_next_backup', false],
			[__('Set DB Sizes'), 'set_db_sizes', true],
			[__('Retry Failed Backups'), 'retry_failed_backups', true],
			[__('Delete Backups'), 'delete_backups', true],
			[__('Activate All Sites'), 'activate_all_sites', true],
		].forEach(([label, method, grouped]) => {
			frm.add_custom_button(
				label,
				() => {
					frappe.confirm(
						`Are you sure you want to ${label.toLowerCase()}?`,
						() => frm.call(method).then(() => frm.refresh()),
					);
				},
				grouped ? __('Actions') : null,
			);
		});
	},
});
