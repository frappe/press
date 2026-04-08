// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('NAT Server', {
	refresh(frm) {
		[
			[__('Prepare Server'), 'prepare_server', true, !frm.doc.is_server_setup],
			[__('Setup Server'), 'setup_server', true, !frm.doc.is_server_setup],
			[__('Ping Ansible'), 'ping_ansible', true, frm.doc.is_server_setup],
			[__('Archive Server'), 'archive', true, frm.doc.is_server_setup],
			[__('Get Static IP'), 'get_static_ip', true, !frm.doc.is_static_ip],
			[__('Attach NAT Security Group'), 'attach_nat_security_group', true],
			[
				__('Configure Monitoring'),
				'configure_monitoring',
				true,
				frm.doc.is_server_setup,
			], // added temporarily for setting up nginx & monitoring config
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (confirm) {
							frappe.confirm(
								`Are you sure you want to ${label.toLowerCase()}?`,
								() =>
									frm.call(method).then((r) => {
										if (r.message) {
											frappe.msgprint(r.message);
										} else {
											frm.refresh();
										}
									}),
							);
						} else {
							frm.call(method).then((r) => {
								if (r.message) {
									frappe.msgprint(r.message);
								} else {
									frm.refresh();
								}
							});
						}
					},
					__('Actions'),
				);
			}
		});

		if (frm.doc.status === 'Active' && !!frm.doc.secondary_private_ip) {
			frm.add_custom_button(
				__('Trigger Failover'),
				() => {
					let d = new frappe.ui.Dialog({
						title: __('Select Failover Instance'),
						fields: [
							{
								label: __('Secondary NAT Server'),
								fieldname: 'secondary',
								fieldtype: 'Link',
								options: 'NAT Server',
								reqd: 1,
								get_query: function () {
									return {
										filters: {
											name: ['!=', frm.doc.name],
											status: 'Active',
											cluster: frm.doc.cluster,
											secondary_private_ip: ['is', 'not set'],
										},
									};
								},
							},
						],
						primary_action_label: __('Trigger Failover'),
						primary_action(values) {
							frm
								.call({
									doc: frm.doc,
									method: 'trigger_failover',
									args: {
										secondary: values.secondary,
									},
								})
								.then((r) => {
									if (r.message) {
										frappe.msgprint(r.message);
									}
								});
							d.hide();
						},
					}).show();
				},
				__('Actions'),
			);
		}
	},
});
