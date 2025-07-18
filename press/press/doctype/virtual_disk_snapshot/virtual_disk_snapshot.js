// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Disk Snapshot', {
	refresh: function (frm) {
		[
			[__('Sync'), 'sync'],
			[__('Delete'), 'delete_snapshot'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm.call(method).then((r) => frm.refresh());
				},
				__('Actions'),
			);
		});
		if (frm.doc.snapshot_id) {
			frm.add_web_link(
				`https://${frm.doc.region}.console.aws.amazon.com/ec2/v2/home?region=${frm.doc.region}#SnapshotDetails:snapshotId=${frm.doc.snapshot_id}`,
				__('Visit AWS Dashboard'),
			);
		}
	},
});
