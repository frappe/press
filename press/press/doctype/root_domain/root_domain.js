// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Root Domain', {
	refresh: function (frm) {
		frm.trigger('set_mandatory_fields');
		frm.add_custom_button('Add to proxies', () => {
			frm.call('add_to_proxies').then((r) => frm.refresh());
		});
	},

	dns_provider: function (frm) {
		frm.trigger('set_mandatory_fields');
	},

	set_mandatory_fields: function (frm) {
		frm.set_df_property(
			'aws_access_key_id',
			'reqd',
			frm.doc.dns_provider === 'AWS Route 53',
		);
		frm.set_df_property(
			'aws_secret_access_key',
			'reqd',
			frm.doc.dns_provider === 'AWS Route 53',
		);
		frm.set_df_property(
			'cloud_flare_api_key',
			'reqd',
			frm.doc.dns_provider === 'Cloud Flare',
		);
	},
});
