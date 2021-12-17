// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Group', {
	onload: function (frm) {
		if (frm.is_new()) {
			frm.call('validate_dependencies');
		}
	},
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.name}`,
			__('Visit Dashboard')
		);
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