// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Group', {
	refresh: async function(frm) {
        frm.add_custom_button(__('Goto Dashboard'), () => {
            let host_name = window.location.host;
            let protocol = ['frappecloud.com', 'staging.frappe.cloud'].includes(host_name) ? 'https://' : 'http://';
            window.location.href = `${protocol}${host_name}/dashboard/benches/${frm.doc.name}`;
        });
		[
			[
				__('Create Deploy Candidate'),
				'press.api.bench.create_deploy_candidate',
			],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm
						.call({
							method,
							freeze: true,
							args: {
								name: frm.doc.name,
							},
						})
						.then(({
							message
						}) => {
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
		});
		frm.set_df_property('dependencies', 'cannot_add_rows', 1);
	},
});