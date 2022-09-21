// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine', {
	refresh: function (frm) {
		[
			[__('Sync'), 'sync'],
			[__('Reboot'), 'reboot'],
			[__('Terminate'), 'terminate', !frm.doc.termination_protection],
			[__('Disable Termination Protection'), 'disable_termination_protection', frm.doc.termination_protection],
			[__('Enable Termination Protection'), 'enable_termination_protection', !frm.doc.termination_protection],
			[__('Create Image'), 'create_image'],
			[__('Create Proxy Server'), 'create_proxy_server', frm.doc.series === "n"],
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
		if (frm.doc.aws_instance_id){
			frm.add_web_link(`https://${frm.doc.region}.console.aws.amazon.com/ec2/v2/home?region=${frm.doc.region}#InstanceDetails:instanceId=${frm.doc.aws_instance_id}`, __('Visit AWS Dashboard'));
		}
	}
});
