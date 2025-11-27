// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Proxy Failover', {
	refresh(frm) {
		frm.add_custom_button(
			'Route Requests From Primary To Secondary',
			() => {
				frm.call('create_agent_job_for_routing_requests');
			},
			'Actions',
		);
	},
});
