// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bench', {
	onload: function (frm) {
		frm.set_query("candidate", function () {
			return {
				"filters": {
					"group": frm.doc.group,
				}
			};
		});
	},

	refresh: function (frm) {
		[
			[__('Archive'), 'archive'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm.call(method).then((r) => frappe.msgprint(r.message));
				},
				__('Actions')
			);
		});
	}
});
