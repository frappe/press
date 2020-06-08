// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release', {
	refresh: function (frm) {
		[
			[__('Request Approal'), 'request_approval'],
			[__('Approve'), 'approve'],
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
