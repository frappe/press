// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Add On Settings', {
	refresh: function(frm) {

		create_custom_button(
			frm, 
			"Reset etcd Admin Data", 
			"init_etcd_data"
		);

	}
});

function create_custom_button(frm, title, method) {
	return frm.add_custom_button(
		__(title),
		() => {
			frappe.prompt(
				{ fieldtype: 'Data', label: 'Proxy Server Name', fieldname: 'proxy_server', reqd: 1 },
				({ proxy_server }) => {
					frm.call(method, { proxy_server: proxy_server });
				}
			);
		},
		'Actions'
	);
}
