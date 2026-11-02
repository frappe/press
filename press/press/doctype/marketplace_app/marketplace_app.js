// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Marketplace App', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/apps/${frm.doc.name}/`,
			__('Open in dashboard'),
		);

		// add custom button to run audit for the marketplace app - only show if the marketplace app has bypass_automated_audit set to False
		if (!frm.doc.bypass_automated_audit) {
			frm.add_custom_button(__('Run Audit'), () => {
				frappe
					.call(
						'press.press.doctype.marketplace_app.marketplace_app.run_audit_for_marketplace_app',
						{
							marketplace_app: frm.doc.name,
							app_release: frm.doc.latest_release,
						},
					)
					.then((r) => {
						frappe.msgprint('Audit triggered successfully: ' + r.message);
						frm.refresh();
					});
			});
		}
	},
});
