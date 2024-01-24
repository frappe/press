// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serial Console Log', {
	refresh(frm) {
		frappe.realtime.off('serial_console_log_update');
		frappe.realtime.on('serial_console_log_update', (message) => {
			if (message.name == frm.doc.name) {
				frm.set_value('output', message.output);
			}
		});
	},
});
