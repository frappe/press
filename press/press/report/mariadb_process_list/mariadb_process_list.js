// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["MariaDB Process List"] = {
	onload: function(report) {
		report.page.add_button(
				__('Kill Processes'),
				() => {
					const dialog = new frappe.ui.Dialog({
						title: __('Kill Processes'),
						fields: [{
							fieldtype: 'Int',
							default: 120,
							label: __('Kill Proceeses Running Longer Than (Seconds)'),
							fieldname: 'kill_threshold',
						}]
					});
					
					dialog.set_primary_action(__('Kill Processes'), args => {
						frappe.call('press.press.report.mariadb_process_list.mariadb_process_list.kill',
							{
								database_server: frappe.query_report.get_filter_value('database_server'),
								kill_threshold: args.kill_threshold
							}
						).then((r) => {
							dialog.hide();
							frappe.query_report.refresh()
						})
					});
					dialog.show();
				},
			);
		}
};
