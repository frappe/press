// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.group}/deploys/${frm.doc.name}`,
			__('Visit Dashboard'),
		);

		frm.fields_dict['apps'].grid.get_field('app').get_query = function (doc) {
			return {
				query: 'press.press.doctype.deploy_candidate.deploy_candidate.desk_app',
				filters: { release_group: doc.group },
			};
		};

		const actions = [
			[
				__('Generate Build Context'),
				'generate_build_context',
				window.dev_server,
			],
			[__('Build'), 'build', true],
			[__('Build without cache'), 'build_without_cache', true],
			[__('Build without push'), 'build_without_push', window.dev_server],
			[__('Deploy to Staging'), 'deploy_to_staging', true],
			[__('Promote to Production'), 'promote_to_production', frm.doc.staged],
			[
				__('Deploy to Production (build and deploy)'),
				'deploy_to_production',
				true,
			],
			[
				__('Cleanup Build Directory'),
				'cleanup_build_directory',
				frm.doc.status !== 'Draft',
			],
		];

		for (const [label, method, show] of actions) {
			if (!show) {
				continue;
			}

			frm.add_custom_button(
				label,
				() => frm.call(method).then((r) => frm.refresh()),
				__('Actions'),
			);
		}

		add_redeploy(frm);
	},
});

function add_redeploy(frm) {
	/**
	 * The methods `fail_and_redeploy` and `redeploy` create
	 * a new Deploy Candidate from the linked Release Group
	 * and trigger `deploy_candidate.build_and_deploy`.
	 */

	let method = 'fail_and_redeploy';
	let label = __('Fail and Redeploy');

	if (['Draft', 'Failure', 'Success'].includes(frm.doc.status)) {
		method = 'redeploy';
		label = __('Redeploy');
	}

	frm.add_custom_button(label, handler, __('Actions'));
	async function handler() {
		const { message } = await frm.call(method);

		frappe.msgprint({
			title: __('Redeploy Triggered'),
			indicator: 'green',
			message: __(`Duplicate {0} created and redeploy triggered.`, [
				`<a href="/app/deploy-candidate/${message.name}">Deploy Candidate</a>`,
			]),
		});

		frm.refresh();
	}
}
