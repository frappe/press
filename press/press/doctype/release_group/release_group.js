// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.require('assets/press/js/ListComponent.js');
frappe.require('assets/press/js/utils.js');
frappe.require('assets/press/js/DetailedListComponent.js')
frappe.require('assets/press/js/SectionHead.js')


frappe.ui.form.on('Release Group', {
	onload: async function (frm) {
		// data fetch
		let versions_res = await frappe.call({
			method: 'press.api.bench.versions',
			args: { name: frm.docname },
		});
		let apps_res = await frappe.call({
			method: 'press.api.bench.apps',
			args: { name: frm.docname },
		});
		let recent_deploys_res = await frappe.call({
			method: 'press.api.bench.recent_deploys',
			args: { name: frm.docname },
		});
		let deploys_log_res = await frappe.call({
			method: 'press.api.bench.candidates',
			args: { name: frm.docname }, 
		});
		let jobs_log_res = await frappe.call({
			method: 'press.api.bench.jobs',
			args: { name: frm.docname }
		})

		// data remaps
		let versions = remap(versions_res.message, (d) => {
			return {
				name: d.name,
				length: d.sites.length,
			};
		});
		let apps = remap(apps_res.message, (d) => {
			return {
				data: d,
			};
		});
		let recent_deploys = remap(recent_deploys_res.message, (d) => {
			return {
				data: d,
			};
		});
		let sites = remap(versions_res.message, (d) => {
			return {
				sites: d.sites,
				bench_name: d.name,
			};
		});
		let deploys_log = remap(deploys_log_res.message, (d) => {
			return {
				title: "Deploy on " + d.creation,
				message: d.apps, // break this array into string
				tag: d.status,
				tag_type: "indicator-pill green",
				name: d.name,
				type: d.name
			}
		});
		let jobs_log = remap(jobs_log_res.message, (d) => {
			return {
				title: d.job_type,
				message: d.end,
				tag: d.status,
				tag_type: "indicator-pill green",
				name: d.name,
				type: d.name
			}
		})

		// sec: Overview
		new ListComponent(frm.get_field('bench_versions_block').$wrapper, {
			data: versions,
			template: version_template,
		});
		new ListComponent(frm.get_field('apps_list_block').$wrapper, {
			data: apps,
			template: app_template,
		});
		new ListComponent(frm.get_field('recent_deploys_block').$wrapper, {
			data: recent_deploys,
			template: deploys_template,
		});

		// sec: Sites
		new ListComponent(frm.get_field('sites_block').$wrapper, {
			data: sites,
			template: sites_template,
		});

		// sec: Deploys
		new DetailedListComponent(frm.get_field('deploys_section_block').$wrapper, {
			title: 'Deploys',
			description: 'Deploys on your bench',
			data: deploys_log,
			template: title_with_message_and_tag_template,
			onclick: async (index, wrapper) => {
				let steps = await frappe.call({
					method: 'press.api.bench.candidate',
					args: {
						name: deploys_log[index].name
					}
				});

				new SectionHead(wrapper, {
					title: 'Build log',
					description: 'Completed 1 month ago in'
				});

				let deploy_lines = remap(steps.message.build_steps, (d) => {
					return {
						step_title: d.stage + " - " + d.step,
						step_detail: d.output == "" || d.output == undefined ? "No output" : d.output
					}
				});

				new ListComponent(wrapper, {
					data: deploy_lines,
					template: log_template
				})
			}
		})

		// sec: Jobs
		new DetailedListComponent(frm.get_field('jobs_block').$wrapper, {
			title: 'Jobs',
			description: 'History of jobs that ran on your bench',
			data: jobs_log,
			template: title_with_message_and_tag_template,
			onclick: async (index, wrapper) => {
				let steps = await frappe.call({
					method: 'press.api.site.job',
					args: {
						job: jobs_log[index].name
					}
				});

				new SectionHead(wrapper, {
					title: jobs_log[index].title,
					description: 'Completed 6 hours ago in 0:00:39'
				});

				let job_lines = remap(steps.message.steps, (d) => {
					return {
						step_title: d.step_name,
						step_detail: d.output ? d.output : "No output"
					}
				});

				new ListComponent(wrapper, {
					data: job_lines,
					template: log_template
				})
			}
		})

		frm.doc.created_on = frm.doc.apps[0].creation;

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
		});
		frm.set_df_property('dependencies', 'cannot_add_rows', 1);
	},
});

// custom templates
let version_template = (data) => {
	return `
		<div class="d-flex flex-row justify-between">
			<p>${data.name}</p> 
			<span class="indicator-pill green">${data.length} sites</span>
		</div>
	`;
};

let app_template = (data) => {
	return `
		<div class="d-flex flex-column justify-between">
			<h5>${data.data.name}</h5>
			<p>${data.data.repository_owner}/${data.data.repository}:${data.data.branch}</p>	
		</div>
	`;
};

let deploys_template = (data) => {
	let date = new Date(data.data.creation);

	let month = date.toLocaleString('default', { month: 'long' });

	return `
		<div class="d-flex flex-column justify-between">
			<p>
			Deployed on ${date.getDate()} ${month} ${date.getFullYear()}, ${date.getHours()}:${date.getMinutes()} GMT+5:30
			</p>
		</div>
	`;
};

let sites_template = (data) => {
	let template = '';

	for (let site of data.sites) {
		template += `
			<div class="d-flex flex-row justify-between">
				<p class="list-row-col ellipsis list-subject level">${site.name}
				<p class="list-row-col ellipsis hidden-xs">${data.bench_name}</p>
				<div class="list-row-col ellipsis hidden-xs">
					<p class="indicator-pill ${
						site.status === 'Active' ? 'green' : 'red'
					} ellipsis">${site.status}</p>
				</div>
				<button class="btn btn-outline-primary ellipsis" onclick="navigate">
					Visit Site
				</button>
			</div>
			<hr>
		`;
	}

	return template;
};