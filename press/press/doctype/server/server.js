// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server', {
	refresh: function (frm) {
		[
			[__('Ping Agent'), "ping_agent", false, frm.doc.is_server_setup],
			[__('Ping Ansible'), "ping_ansible", true],
			[__('Ping Ansible Scaleway'), "ping_ansible_scaleway", true],
			[__('Update Agent'), "update_agent", true, frm.doc.is_server_setup],
			[__('Prepare Scaleway Server'), "prepare_scaleway_server", true, !frm.doc.is_server_setup && frm.doc.provider === "Scaleway"],
			[__('Setup Server'), "setup_server", true, !frm.doc.is_server_setup],
			[__('Add to Proxy'), "add_upstream_to_proxy", true, frm.doc.is_server_setup && !frm.doc.is_upstream_setup],
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === "undefined" || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (confirm) {
							frappe.confirm(
								`Are you sure you want to ${label.toLowerCase()}?`,
								() => frm.call(method).then((r) => {
									if (r.message) {
										frappe.msgprint(r.message);
									} else {
										frm.refresh();
									}
								})
							);

						} else {
							frm.call(method).then((r) => {
								if (r.message) {
									frappe.msgprint(r.message);
								} else {
									frm.refresh();
								}
							})
						}
					},
					__('Actions')
				);
			}
		});
	}
});