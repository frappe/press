// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Group', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.name}`,
			__('Visit Dashboard')
		);
		frm.add_custom_button(
			__('Create Deploy Candidate'),
			() => {
				frm
					.call({
						method: 'press.api.bench.create_deploy_candidate',
						freeze: true,
						args: {
							name: frm.doc.name,
						},
					})
					.then(({ message }) => {
						frappe.msgprint({
							title: __('New Deploy Candidate Created'),
							indicator: 'green',
							message: __(
								`New <a href="/app/deploy-candidate/${message.name}">Deploy Candidate</a> for this bench was created successfully.`
							),
						});

						frm.refresh();
					});
			},
			__('Actions')
		);

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
						});
					},
				});
				d.show();
			},
			__('Actions')
		);

		frm.set_df_property('dependencies', 'cannot_add_rows', 1);
	},
	version: function (frm) {
		if (frm.is_new()) {
			frm.clear_table('dependencies');
			frm.call('validate_dependencies');
		}
	},
});
