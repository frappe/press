// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.group}/deploys/${frm.doc.name}`,
			__('Visit Dashboard')
		);

		frm.fields_dict['apps'].grid.get_field('app').get_query = function (doc) {
			return {
				"query": "press.press.doctype.deploy_candidate.deploy_candidate.desk_app",
				"filters": { 'release_group': doc.group }
			}
		};

		[
			[__('Build'), 'build', true],
			[__('Build without cache'), 'build_without_cache', true],
			[__('Deploy to Staging'), 'deploy_to_staging', true],
			[__('Promote to Production'), 'promote_to_production', frm.doc.staged],
			[__('Deploy to Production (build and deploy)'), 'deploy_to_production', true],
		].forEach(([label, method, show]) => {
			if (show)
				frm.add_custom_button(
					label,
					() => { frm.call(method).then((r) => frm.refresh()) },
					__('Actions')
				);
		});

	}
});
