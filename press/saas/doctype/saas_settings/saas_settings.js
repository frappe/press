// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Saas Settings', {
	 refresh: function(frm) {
		frm.set_query('plan', () => {
			return {
				'filters': {'app': frm.doc.name, 'is_free': 1}
			}
		});
	 }
});
