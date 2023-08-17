// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stack', {
	refresh(frm) {
		[[__('Deploy'), 'deploy']].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm.call(method).then(({ response }) => {
						frappe.msgprint(response.message);
						frm.refresh();
					});
				},
				__('Actions'),
			);
		});
	},
});
