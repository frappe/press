// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inspect Trace ID', {
	refresh(frm) {
		frm.disable_save();
	},
	trace_id(frm) {
		if (frm.doc.trace_id) {
			frm.call('fetch');
		}
	},
});
