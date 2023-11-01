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
		if (frm.doc.aws_vpc_id) {
			frm.add_web_link(
				`https://${frm.doc.region}.console.aws.amazon.com/vpc/home?region=${frm.doc.region}#VpcDetails:VpcId=${frm.doc.aws_vpc_id}`,
				__('Visit AWS Dashboard'),
			);
		}
	},
});
