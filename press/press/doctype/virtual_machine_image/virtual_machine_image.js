// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine Image', {
	refresh: function (frm) {
		[
			[__('Sync'), 'sync'],
			[__('Delete'), 'delete_image'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm.call(method).then((r) => frm.refresh());
				},
				__('Actions'),
			);
		});
		frm.add_custom_button(
			__('Copy'),
			() => {
				const dialog = new frappe.ui.Dialog({
					title: __('Copy'),
					fields: [
						{
							fieldtype: 'Link',
							options: 'Cluster',
							label: __('Destination Cluster'),
							fieldname: 'cluster',
							get_query: () => {
								return {
									filters: [
										['name', '!=', frm.doc.cluster],
										['cloud_provider', '=', 'AWS EC2'],
									],
								};
							},
						},
					],
				});
				dialog.set_primary_action(__('Copy'), (args) => {
					frm
						.call('copy_image', {
							cluster: args.cluster,
						})
						.then((r) => {
							console.log(r);
							dialog.hide();
							frm.refresh();
						});
				});
				dialog.show();
			},
			__('Actions'),
		);
		if (frm.doc.aws_ami_id) {
			frm.add_web_link(
				`https://${frm.doc.region}.console.aws.amazon.com/ec2/v2/home?region=${frm.doc.region}#ImageDetails:imageId=${frm.doc.aws_ami_id}`,
				__('Visit AWS Dashboard'),
			);
		}
	},
});
