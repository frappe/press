// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agent Job', {
	refresh: function (frm) {
		frm.add_custom_button(__('Retry'), () => {
			frappe.confirm(
				`Are you sure you want to retry this job?`,
				() => frm.call("retry").then((result) => frappe.msgprint(result.message.name))
			);
		});
	}
});
