// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bare Metal Firewall Rule', {
	refresh: function(frm) {
		// Clear port fields when protocol is ICMP
		if (frm.doc.protocol === 'icmp') {
			frm.set_value('from_port', '');
			frm.set_value('to_port', '');
		}
	},

	protocol: function(frm) {
		// Clear port fields when switching to ICMP
		if (frm.doc.protocol === 'icmp') {
			frm.set_value('from_port', '');
			frm.set_value('to_port', '');
		}
	},

	from_port: function(frm) {
		// Set to_port same as from_port if empty
		if (frm.doc.from_port && !frm.doc.to_port) {
			frm.set_value('to_port', frm.doc.from_port);
		}
	}
}); 