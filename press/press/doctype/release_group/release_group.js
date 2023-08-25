// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Group', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.name}`,
			__('Visit Dashboard'),
		);
		[
			[__('Create Deploy Candidate'), 'create_deploy_candidate'],
			[
				__('Create Duplicate Deploy Candidate'),
				'create_duplicate_deploy_candidate',
			],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm.call(method).then(({ message }) => {
						frappe.msgprint({
							title: __('New Deploy Candidate Created'),
							indicator: 'green',
							message: __(`New {0} for this bench was created successfully.`, [
								`<a href="/app/deploy-candidate/${message.name}">Deploy Candidate</a>`,
							]),
						});
						frm.refresh();
					});
				},
				__('Actions'),
			);
		});

		frm.add_custom_button(
			'Change Server',
			() => {
				let d = new frappe.ui.Dialog({
					title: 'Change Server',
					fields: [
						{
							fieldtype: 'Link',
							fieldname: 'server',
							label: 'Server',
							options: 'Server',
							reqd: 1,
						},
					],
					primary_action({ server }) {
						frm.call('change_server', { server }).then((r) => {
							if (!r.exc) {
								frappe.show_alert(`Server changed to ${server}`);
							}
							d.hide();
						});
					},
				});
				d.show();
			},
			__('Actions'),
		);
		frm.add_custom_button(
			'Add Server',
			() => {
				let d = new frappe.ui.Dialog({
					title: 'Add Server',
					fields: [
						{
							fieldtype: 'Link',
							fieldname: 'server',
							label: 'Server',
							options: 'Server',
							reqd: 1,
						},
					],
					primary_action({ server }) {
						frm.call('add_server', { server, deploy: true }).then((r) => {
							if (!r.exc) {
								frappe.show_alert(
									`Added ${server} and deployed last successful candidate`,
								);
							}
							d.hide();
						});
					},
				});
				d.show();
			},
			__('Actions'),
		);

		frm.set_df_property('dependencies', 'cannot_add_rows', 1);
	},
});
