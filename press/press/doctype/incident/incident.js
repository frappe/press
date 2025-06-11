// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident', {
	refresh(frm) {
		[
			[__('Ignore Incidents on Server'), 'ignore_for_server'],
			[__('Reboot Database Server'), 'reboot_database_server'],
			[__('Restart Down Benches'), 'restart_down_benches'],
			[__('Take Grafana screenshots'), 'regather_info_and_screenshots'],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()}?`,
							() => frm.call(method).then((r) => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});
		frm.call('get_down_site').then((r) => {
			if (!r.message) return;
			frm.add_web_link(`https://${r.message}`, __('Visit Down Site'));
		});
	},
});
