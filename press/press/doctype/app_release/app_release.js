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

		frm.add_custom_button(
			__('View'),
			() => {
				window.open(frm.doc.code_server_url);
			},
		);

		if (frm.doc.result_html) {
			let wrapper = frm.get_field("result_html_rendered").$wrapper;
			wrapper.html(frm.doc.result_html);
		}
	},
});
