// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('User SSH Certificate', {
	refresh: function(frm) {
		frm.toggle_reqd('access_server', !(frm.doc.all_server_access));

		if (frm.doc.docstatus === 1){
			let key_type = frm.doc.ssh_public_key.split(" ")[0].split("-")[1];
			frm.add_custom_button('Copy Certificate Details', function() {
				let text = `echo '${frm.doc.ssh_certificate.trim()}' > ~/.ssh/id_${key_type}-cert.pub`
				copy_to_clipboard(text)
			});
			if (!frm.doc.all_server_access) {
				frm.add_custom_button('Copy SSH Command', function() {
					copy_to_clipboard(frm.doc.ssh_command)
				});
			}
			frm.set_df_property("ssh_certificate", "description", `Save this certificate on your system under ~/.ssh/id_${key_type}-cert.pub`);
		}
	},
	all_server_access: (frm) => {
		frm.toggle_reqd('access_server', !(frm.doc.all_server_access));
	},
	is_self_hosted: (frm) => {
		frm.set_value('access_server', 'gateway.erpnext.com');
		frm.set_df_property("ssh_certificate", "read_only", 1);

	},
});

function copy_to_clipboard(text) {
	frappe.utils.copy_to_clipboard(text)
	frappe.show_alert({
		indicator: 'green',
		message: __('Paste the command in your system terminal.')
	});
}
