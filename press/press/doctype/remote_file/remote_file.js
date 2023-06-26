// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Remote File', {
	refresh: function (frm) {
		frm.add_custom_button(
			__('Download'),
			() => {
				frm.call('get_download_link').then((r) => {
					if (!r.exc) {
						window.open(r.message);
					}
				});
			},
			__('Actions'),
		);
		frm.add_custom_button(
			__('Delete File'),
			() => {
				frappe.confirm(
					`Doing this won't allow you to restore the Site again using this backup. Are you sure you want to delete this file from S3?`,
					() => frm.call('delete_remote_object').then((r) => frm.refresh()),
				);
			},
			__('Actions'),
		);
		frm.add_custom_button(
			__('Ping'),
			() => {
				frm.call('exists').then((r) => {
					if (!r.exc) {
						if (r.message) {
							console.log(r.message);
							frappe.msgprint('Pong');
						} else {
							frm.refresh();
							frm.refresh_header();
						}
					}
				});
			},
			__('Actions'),
		);
	},
});
