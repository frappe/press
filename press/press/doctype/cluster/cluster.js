// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cluster', {
	refresh: function (frm) {
		if (frm.doc.aws_vpc_id) {
			frm.add_web_link(
				`https://${frm.doc.region}.console.aws.amazon.com/vpc/home?region=${frm.doc.region}#VpcDetails:VpcId=${frm.doc.aws_vpc_id}`,
				__('Visit AWS Dashboard'),
			);
		}
	},
});
