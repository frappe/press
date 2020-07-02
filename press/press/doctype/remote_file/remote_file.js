// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Remote File', {
	refresh: function(frm){
		frm.add_custom_button(__('Download'), function() {
			frm.events.download(frm);
		});
	},
	download: function(frm){
		frm.call("get_download_link").then(r => {
			if(!r.exc) {
				window.open(r.message);
			}
		});
	}
});
