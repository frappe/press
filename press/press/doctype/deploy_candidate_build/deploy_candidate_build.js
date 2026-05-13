// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt
frappe.ui.form.on('Deploy Candidate Build', {
	refresh(frm) {
		frm.add_web_link(
			`/dashboard/groups/${frm.doc.group}/deploys/${frm.doc.name}`,
			__('Visit Dashboard'),
		);
		[
			[
				__('Cleanup Directory'),
				'cleanup_build_directory',
				typeof frm.doc.build_directory !== 'undefined' &&
					frm.doc.status !== 'Running',
				{},
				'Build',
			],
			[
				__('Stop And Fail'),
				null,
				!['Success', 'Failure', 'Running'].includes(frm.doc.status),
				{},
				'Build',
			],
			[__('Fail Remote Job'), null, frm.doc.status === 'Running', {}, 'Build'],
			[
				__('Fail and Redeploy'),
				null,
				!['Success', 'Failure', 'Running'].includes(frm.doc.status),
				{},
				'Build',
			],
			[__('Deploy'), 'deploy', frm.doc.status === 'Success', {}, 'Deploy'],
			[
				__('Redeploy'),
				'redeploy',
				['Draft', 'Failure', 'Success'].includes(frm.doc.status),
				{ no_cache: false },
				'Deploy',
			],
			[
				__('Redeploy (No Cache)'),
				'redeploy',
				['Draft', 'Failure', 'Success'].includes(frm.doc.status),
				{ no_cache: true },
				'Deploy',
			],
		].forEach(([label, method, condition, args, group]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (label === 'Stop And Fail') {
							frappe.call(
								'press.press.doctype.deploy_candidate_build.deploy_candidate_build.stop_and_fail',
								{
									dn: frm.doc.name,
								},
							);
						} else if (label == 'Fail Remote Job') {
							frappe.call(
								'press.press.doctype.deploy_candidate_build.deploy_candidate_build.fail_remote_job',
								{
									dn: frm.doc.name,
								},
							);
						} else if (label == 'Fail And Redeploy') {
							frappe.call(
								'press.press.doctype.deploy_candidate_build.deploy_candidate_build.fail_and_redeploy',
								{
									dn: frm.doc.name,
								},
							);
						} else {
							frm.call(method, args).then((r) => {
								if (!r) {
									return;
								}

								const { error, message } = r.message;

								if (error) {
									frappe.msgprint({
										title: 'Action Failed',
										indicator: 'yellow',
										message: message,
									});
								}

								if (method === 'deploy') {
									frappe.msgprint({
										title: 'Deploy Triggered',
										indicator: 'green',
										message: __(`Created a new {0}`, [
											`<a href="/app/deploy/${message}">Deploy</a>`,
										]),
									});
								} else if (method === 'redeploy') {
									frappe.msgprint({
										title: 'Redeploy Triggered',
										indicator: 'green',
										message: __(
											`Duplicate {0} created and redeploy triggered.`,
											[
												`<a href="/app/deploy-candidate/${message}">Deploy Candidate</a>`,
											],
										),
									});
								} else if (method === 'create_arm_build') {
									// TODO: Fix the message later!
									frappe.msgprint({
										title: 'ARM Build Triggered',
										indicator: 'green',
										message: __(`Created a new {0}`, [
											`<a href="/app/deploy-candidate-build/${r.message}">Deploy Candidate Build</a>`,
										]),
									});
								}
							});
						}
					},
					group,
				);
			}
		});
	},
});
