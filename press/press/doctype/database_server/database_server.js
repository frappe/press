// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Database Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard')
		);
		[
			[__('Ping Agent'), "ping_agent", false, !frm.doc.is_server_setup],
			[__('Ping Ansible'), "ping_ansible", true, frm.doc.is_server_prepared],
			[__('Ping Ansible Unprepared'), "ping_ansible_unprepared", true, !frm.doc.is_server_prepared],
			[__('Update Agent'), "update_agent", true, frm.doc.is_server_setup],
			[__('Fetch Keys'), "fetch_keys", true, frm.doc.is_server_setup && (!frm.doc.frappe_public_key || !frm.doc.root_public_key)],
			[__('Prepare Server'), "prepare_server", true, !frm.doc.is_server_prepared],
			[__('Setup Server'), "setup_server", true, !frm.doc.is_server_setup],
			[__('Setup Rename'), "rename_server", true, frm.doc.is_server_setup && frm.doc.is_server_prepared && !frm.doc.is_server_renamed],
			[__('Convert From Frappe Server'), "convert_from_frappe_server", true, frm.doc.is_server_setup],
			[__('Setup Replication'), "setup_replication", true, frm.doc.is_server_setup && !frm.doc.is_primary && !frm.doc.is_replication_setup],
			[__('Trigger Failover'), "trigger_failover", true, frm.doc.is_server_setup && !frm.doc.is_primary && frm.doc.is_replication_setup],
			[__('Reset Root Password'), "reset_root_password", true, frm.doc.is_server_setup],
			[__('Setup Deadlock Logger'), "setup_deadlock_logger", true, frm.doc.is_server_setup],
			[__('Fetch Keys'), "fetch_keys", false, frm.doc.is_server_setup && (!frm.doc.frappe_public_key || !frm.doc.root_public_key)],
			[__('Update TLS Certificate'), "update_tls_certificate", true],
			[__('Create Image'), 'create_image', true, frm.doc.status == "Active"],
			[__('Archive'), "archive", true, frm.doc.status !== "Archived"],
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
