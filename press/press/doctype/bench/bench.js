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
			[__('Sync Sites Info'), 'sync_info'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frappe.confirm(
						`Are you sure you want to ${label.toLowerCase()} this bench?`,
						() => frm.call(method).then((r) => frm.refresh())
					);
				},
				__('Actions')
			);
		});
	}
});
