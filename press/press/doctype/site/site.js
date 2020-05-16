// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {
	onload: function (frm) {
		frm.set_query('bench', function () {
			return {
				filters: {
					server: frm.doc.server,
					status: 'Active',
				},
			};
		});
	},
	refresh: function (frm) {
		frm.add_web_link(`https://${frm.doc.name}`, __('Visit Site'));
		frm.add_web_link(
			`/dashboard/#/sites/${frm.doc.name}/general`,
			__('Visit Dashboard')
		);

		[
			[__('Archive'), 'archive'],
			[__('Archive'), 'archive'],
			[__('Backup'), 'backup'],
			[__('Reinstall'), 'reinstall'],
			[__('Restore'), 'restore'],
			[__('Update'), 'schedule_update'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm.call(method).then((r) => frappe.msgprint(r.message));
				},
				__('Actions')
			);
		});
	},
});
