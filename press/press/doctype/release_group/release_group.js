// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.require('assets/press/js/ListComponent.js');
frappe.require('assets/press/js/utils.js');
frappe.require('assets/press/js/DetailedListComponent.js')
frappe.require('assets/press/js/SectionHead.js')
frappe.require('assets/press/js/ActionBlock.js')


frappe.ui.form.on('Release Group', {
	refresh: async function(frm) {
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
				message: d.name,
				tag: d.sites.length ? `${d.sites.length} sites`: 'Broken',
				tag_type: d.sites.length ? 'indicator-pill green' : 'indicator-pill red'
			};
		});
		let apps = remap(apps_res.message, (d) => {
            return {
                title: d.title,
                message: d.repository + '/' + d.repository + ':' + d.branch,
                tag: d.update_available ? 'Update Availabe' : (d.hash ? d.hash.substring(0,7) : ""),
                tag_type: 'indicator-pill blue'
            };
		});
		let recent_deploys = remap(recent_deploys_res.message, (d) => {
			return {
				message: 'Deployed On ' + format_date_time(d.creation, 1, 1),
			};
		});
		let sites = []
		remap(versions_res.message, (d1) => {
			remap(d1.sites, (d2) => {
				sites.push ({
					title: d2.name,
					sub_text: d1.name,
					tag: d2.status,
					tag_type: "indicator-pill " + (d2.status === 'Active' ? 'green' : 'red'),
					button: {
						title: 'Visit Site',
						onclick: () => {
							frappe.msgprint(__('Visiting Site...'));
						}
					},
				}); 
			})
		})
		let deploys_log = remap(deploys_log_res.message, (d) => {
			return {
				title: "Deploy on " + format_date_time(d.creation, 1, 1),
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
		clear_block(frm, 'update_alert_block');
		new ActionBlock(frm.get_field('update_alert_block').$wrapper, {
			'title': 'Update Available',
			'description': 'A new update is available for your bench. Would you like to deploy the update now?',
			'button': {
				'title': 'Show updates',
				'onclick': () => {

				},
				'tag': 'primary'
			}
		})

		clear_block(frm, 'bench_info_block');
		new SectionHead(frm.get_field('bench_info_block').$wrapper, {
			title: 'Bench Info',
			description: 'General information about your bench'
		})

		clear_block(frm, 'bench_versions_block');
		new SectionHead(frm.get_field('bench_versions_block').$wrapper, {
			title: 'Versions',
			description:'Deployed versions of your bench',
			button: {
				title: 'View versions',
				onclick: () => {
                    frm.scroll_to_field('sites_block');
				}
			}
		})
		new ListComponent(frm.get_field('bench_versions_block').$wrapper, {
			data: versions,
			template: title_with_message_and_tag_template,
		});

		clear_block(frm, 'apps_list_block');
		new SectionHead(frm.get_field('apps_list_block').$wrapper, {
			title: 'Apps',
			description: 'Apps available on your bench',
			button: {
				title: 'Add App',
				onclick: async () => {
					let res = await frappe.call({
						method: 'press.api.bench.installable_apps',
						args: {
							name: frm.docname
						}
					})
					let installable_apps = res.message;
					let app_sources = [];
					for (let i = 0; i < installable_apps.length; i++) {
						for(let j = 0; j < installable_apps[i].sources.length; j++) {
							app_sources.push(installable_apps[i].sources[j].name)
						}
					}
					new frappe.ui.form.MultiSelectDialog({
						doctype: "App Source",
						target: frm,
						setters: {
							app: null,
							branch: null,
						},
						add_filters_group: 0,
						get_query() {
							return {
								filters: { name: ['in', app_sources] }
							}
						},
						async action(selections) {
							// add the app sources to the release group
							for(let i = 0; i < selections.length; i++) {
								let app_source = await frappe.db.get_doc("App Source", selections[i]);
								// Add the selected app to bench using api
								frappe.call({
									method: 'press.api.bench.add_app',
									args: {
										name: frm.docname,
										source: app_source.name,
										app: app_source.app
									}
								}).then((res) => {
									window.location.reload();
								})
							}
						}
					});
                }
			}
		})
		new ListComponent(frm.get_field('apps_list_block').$wrapper, {
			data: apps,
			template: title_with_message_and_tag_template,
		});

		clear_block(frm, 'recent_deploys_block');
		new SectionHead(frm.get_field('recent_deploys_block').$wrapper, {
			title: 'Deploys',
			description: 'History of deploys on your bench',
			button: {
				title: 'View deploys',
				onclick: () => {
                    frm.scroll_to_field('deploys_section_block');
				}
			}
		})
		new ListComponent(frm.get_field('recent_deploys_block').$wrapper, {
			data: recent_deploys,
			template: title_with_message_and_tag_template,
		});

		// sec: Sites
		clear_block(frm, 'sites_block');
		new ListComponent(frm.get_field('sites_block').$wrapper, {
			data: sites,
			template: title_with_sub_text_tag_and_button_template,
			onclick: (i) => {
				// TODO: use frm methods for this redirects
				let host_name = window.location.host;
				let host_name_prefix = ['frappecloud.com', 'staging.frappe.cloud'].includes(host_name) ? 'https://' : 'http://';
				host_name = host_name_prefix + host_name;
				window.location.href = `${host_name}/app/site/${sites[i].title}`;	
			},
		});

		// sec: Deploys
		clear_block(frm, 'deploys_section_block');
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
						title: d.stage + " - " + d.step,
						message: d.output == "" || d.output == undefined ? "No output" : d.output
					}
				});

				new ListComponent(wrapper, {
					data: deploy_lines,
					template: title_with_text_area_template
				})
			}
		})

		// sec: Jobs
		clear_block(frm, 'jobs_block');
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
						title: d.step_name,
						message: d.output ? d.output : "No output"
					}
				});

				new ListComponent(wrapper, {
					data: job_lines,
					template: title_with_text_area_template
				})
			}
		})

		frm.doc.created_on = frm.doc.apps[0].creation;

		if (frm.is_new()) {
			frm.call('validate_dependencies');
		}
	},
});