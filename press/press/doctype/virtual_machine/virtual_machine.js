// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine', {
	refresh: function (frm) {
		[
			[__('Sync'), 'sync'],
			[__('Reboot'), 'reboot', frm.doc.status == "Running"],
			[__('Stop'), 'stop', frm.doc.status == "Running"],
			[__('Start'), 'start', frm.doc.status == "Stopped"],
			[__('Terminate'), 'terminate', !frm.doc.termination_protection],
			[__('Disable Termination Protection'), 'disable_termination_protection', frm.doc.termination_protection],
			[__('Enable Termination Protection'), 'enable_termination_protection', !frm.doc.termination_protection],
			[__('Create Image'), 'create_image', frm.doc.status == "Stopped"],
			[__('Create Server'), 'create_server', frm.doc.series === "f" && frm.doc.status == "Running"],
			[__('Create Database Server'), 'create_database_server', frm.doc.series === "m" && frm.doc.status == "Running"],
			[__('Create Proxy Server'), 'create_proxy_server', frm.doc.series === "n" && frm.doc.status == "Running"],
		].forEach(([label, method, condition]) => {
			if (typeof condition === "undefined" || condition) {
				frm.add_custom_button(
					label,
					() => {
						frm.call(method).then((r) => frm.refresh())
					},
					__('Actions')
				);
			}
		});
		[
			[__('Resize'), 'resize', frm.doc.status == "Stopped"],
		].forEach(([label, method]) => {
			if (typeof condition === "undefined" || condition){	
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt({
							fieldtype: 'Data',
							label: 'Machine Type',
							fieldname: 'machine_type',
							reqd: 1
						},
							({
								machine_type
							}) => {
								frm.call(method, {
									machine_type
								}).then((r) => frm.refresh());
							},
							__('Resize Virtual Machine')
						);
					},
					__('Actions')
				);
			}
		});
		if (frm.doc.aws_instance_id){
			frm.add_web_link(`https://${frm.doc.region}.console.aws.amazon.com/ec2/v2/home?region=${frm.doc.region}#InstanceDetails:instanceId=${frm.doc.aws_instance_id}`, __('Visit AWS Dashboard'));
		}
	}
});
