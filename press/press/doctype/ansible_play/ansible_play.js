// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ansible Play', {
	refresh: function (frm) {
		frappe.realtime.on('ansible_play_progress', (data) => {
			if (data.progress && data.play === frm.doc.name) {
				const progress_title = __('Ansible Play Progress');
				frm.dashboard.show_progress(
					progress_title,
					(data.progress / data.total) * 100,
					`Ansible Play Progress (${data.progress} tasks completed out of ${data.total})`,
				);
				if (data.progress === data.total) {
					frm.dashboard.hide_progress(progress_title);
				}
			}
		});
	},
});
