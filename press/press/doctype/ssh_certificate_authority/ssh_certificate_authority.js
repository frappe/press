// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('SSH Certificate Authority', {
	refresh: function(frm) {
		frm.add_custom_button(
			__('Build Image'),
			() => { frm.call("build_image").then((r) => frm.refresh()) },
			__('Actions')
		);

	}
});
