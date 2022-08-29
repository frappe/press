// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine', {
	refresh: function (frm) {
		frm.add_custom_button(
			"Sync",
			() => {
				frm.call("sync").then(r => frm.refresh());
			},
			__('Actions')
		);
		if (frm.doc.aws_instance_id){
			frm.add_web_link(`https://${frm.doc.region}.console.aws.amazon.com/ec2/v2/home?region=${frm.doc.region}#InstanceDetails:instanceId=${frm.doc.aws_instance_id}`, __('Visit AWS Dashboard'));
		}
	}
});
