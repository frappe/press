// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Storage Integration Subscription', {
	// refresh: function(frm) {

	// }
	enabled(frm, cdt, cdn) {
		frappe.call({
			method: 'press.press.doctype.storage_integration_subscription.storage_integration_subscription.update_user_status',
			args: {
				docname: frm.docname,
				status: frm.fields_dict.enabled.value
			}
		})
	}
});
