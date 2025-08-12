// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cluster', {
	refresh: function (frm) {
		[
			[__('Create Servers'), 'create_servers', frm.doc.status === 'Active'],
			[__('Add Images'), 'add_images', frm.doc.status === 'Active'],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frm.call(method).then((r) => frm.refresh());
					},
					__('Actions'),
				);
			}
		});
		if (frm.doc.vpc_id) {
			if (frm.doc.cloud_provider === 'AWS EC2') {
				frm.add_web_link(
					`https://${frm.doc.region}.console.aws.amazon.com/vpc/home?region=${frm.doc.region}#VpcDetails:VpcId=${frm.doc.vpc_id}`,
					__('Visit AWS Dashboard'),
				);
			} else if (frm.doc.cloud_provider === 'OCI') {
				frm.add_web_link(
					`https://cloud.oracle.com/networking/vcns/${frm.doc.vpc_id}?region=${frm.doc.region}`,
					__('Visit OCI Dashboard'),
				);
			}
		}
		if (frm.doc.cloud_provider === 'AWS EC2' && frm.doc.status === 'Active') {
			// add btn, when clicked creates a prompt and calls check_machine_availability with value input
			frm.add_custom_button(__('Check Machine Availability'), () => {
				frappe.prompt(
					{
						label: __('Machine Type'),
						fieldname: 'machine_type',
						fieldtype: 'Data',
						reqd: 1,
					},
					(values) => {
						frm.call('check_machine_availability', values).then((r) => {
							if (r.message) {
								frappe.show_alert({
									message: __('Machine is available'),
									indicator: 'green',
								});
							} else {
								frappe.show_alert({
									message: __('Machine is not available'),
									indicator: 'red',
								});
							}
						});
					},
					__('Check Machine Availability'),
					__('Check'),
				);
			});
		}
	},
});
