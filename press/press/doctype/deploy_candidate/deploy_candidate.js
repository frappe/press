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

		const can_build = ['Draft', 'Failure', 'Success'].includes(frm.doc.status);
		const can_fail = !can_build;
		const actions = [
			[__('Stop and Fail'), 'stop_and_fail', can_fail, __('Build')],
			[__('Complete'), 'build', can_build, __('Build')],
			[
				__('Generate Context'),
				'generate_build_context',
				can_build,
				__('Build'),
			],
			[__('Without Cache'), 'build_without_cache', can_build, __('Build')],
			[__('Without Push'), 'build_without_push', can_build, __('Build')],
			[
				__('Cleanup Directory'),
				'cleanup_build_directory',
				frm.doc.status !== 'Draft',
				__('Build'),
			],
			[
				__('Schedule Build and Deploy'),
				'schedule_build_and_deploy',
				can_build,
				__('Deploy'),
			],
		];

		for (const [label, method, show, group] of actions) {
			if (!show) {
				continue;
			}

			async function handler() {
				const { message: data } = await frm.call(method);
				if (data.error) {
					frappe.msgprint({
						title: __('Action Failed'),
						indicator: 'yellow',
						message: data.message || `Could not execute ${method}`,
					});
					return;
				}

				frm.refresh();
			}

			frm.add_custom_button(label, handler, group);
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

	frm.add_custom_button(label, handler, __('Deploy'));
	async function handler() {
		const { message: data } = await frm.call(method);
		if (data.error) {
			frappe.msgprint({
				title: __('Cannot Redeploy'),
				indicator: 'yellow',
				message: data.message,
			});
			return;
		}

		frappe.msgprint({
			title: __('Redeploy Triggered'),
			indicator: 'green',
			message: __(`Duplicate {0} created and redeploy triggered.`, [
				`<a href="/app/deploy-candidate/${data.message}">Deploy Candidate</a>`,
			]),
		});

		frm.refresh();
	}
}
