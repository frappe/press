// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Group', {
	refresh: async function(frm) {
        frm.add_custom_button(__('Use Dashboard'), () => {
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
		
		await Promise.all([
            frappe.require('assets/press/js/utils.js'),
            frappe.require('assets/press/js/ListComponent.js'),
            frappe.require('assets/press/js/SectionHead.js'),
            frappe.require('assets/press/js/ActionBlock.js'),
            frappe.require('assets/press/js/DetailedListComponent.js'),
            frappe.require('assets/press/js/AwaitedComponent.js')    
        ])

		let bench_fetch = frappe.call({
			method: 'press.api.bench.get',
			args: {
				name: frm.docname
			}
		});
		let deploy_information_fetch = frm.call('deploy_information');
		let versions_fetch = frappe.call({
			method: 'press.api.bench.versions',
			args: { name: frm.docname },
		});
		let apps_fetch = frappe.call({
			method: 'press.api.bench.apps',
			args: { name: frm.docname },
		});
		let installed_apps_fetch = frappe.call({
			method: 'press.api.bench.installable_apps',
			args: {
				name: frm.docname
			}
		});
		let recent_deploys_fetch = frappe.call({
			method: 'press.api.bench.recent_deploys',
			args: { name: frm.docname },
		});
		let deploy_logs_fetch = frappe.call({
			method: 'press.api.bench.candidates',
			args: { name: frm.docname }, 
		});
		let jobs_logs_fetch = frappe.call({
			method: 'press.api.bench.jobs',
			args: { name: frm.docname }
		});

		// sec: Overview

		clear_block(frm, 'update_alert_block');
		new AwaitedComponent(frm.get_field('update_alert_block').$wrapper, {
			promise: Promise.all([
				bench_fetch,
				deploy_information_fetch
			]),
			onload: ([bench_res, deploy_information_res]) => {
				let bench = bench_res.message;
				let deploy_information = deploy_information_res.message;
				if(deploy_information.update_available && ['Awaiting Deploy', 'Active'].includes(bench.status)) {
					new ActionBlock(frm.get_field('update_alert_block').$wrapper, {
						title: bench.status === 'Active' ? 'Update Available' : 'Deploy',
						description: bench.status === 'Active' ? 
							'A new update is available for your bench. Would you like to deploy the update now?' : 
							'Your bench is not deployed yet. You can add more apps to your bench before deploying. If you want to deploy now, click on Deploy.',
						button: {
							title: 'Show updates',
							onclick: async () => {
								let apps = [];
								// let removed_apps = [];
								for(let app of deploy_information.apps) {
									if(app.update_available) apps.push(app.app);
									// removed_apps.push(deploy_information.removed_apps[i].app);
								}
								new frappe.ui.form.MultiSelectDialog({
									doctype: "App",
									target: frm,
									add_filters_group: 0,
									setters: {
		
									},
									get_query() {
										return {
											filters: { name: ['in', apps] }
										}
									},
									async action(selections) {
										// deploy the selections
										if (selections.length === 0 && deploy_information.removed_apps.length === 0) {
											frappe.msgprint(__('You must select atleast 1 app to proceed with update.'))
											return;
										}
										
										let apps_to_ignore = []
										if (deploy_information) {
											for(let app of deploy_information.apps) {
												if(!selections.includes(app.app) && app.update_available) {
													apps_to_ignore.push(app.app);
												}
											}
										}
										frappe.call({
											method: 'press.api.bench.deploy',
											args: {
												name: bench.name,
												apps_to_ignore: apps_to_ignore
											}
										}).then((ren) => {
											window.location.reload();
											frm.scroll_to_field('deploys_section_block');
										})
									}
								});
							},
							tag: 'primary'
						}
					})
				} else {
					frm.get_field('update_alert_block').$wrapper.remove()
                    frm.refresh_field('update_alert_block');
				}
			}
		})

		clear_block(frm, 'bench_info_block');
		new SectionHead(frm.get_field('bench_info_block').$wrapper, {
			title: 'Bench Info',
			description: 'General information about your bench'
		})

		clear_block(frm, 'bench_versions_block');
		new AwaitedComponent(frm.get_field('bench_versions_block').$wrapper, {
			promise: versions_fetch,
			onload: (versions_res) => {
				let versions = remap(versions_res.message, (d) => {
					return {
						message: d.name,
						tag: `${d.sites.length} sites`,
						tag_type: d.sites.length ? 'indicator-pill green' : 'indicator-pill red'
					};
				});
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
			}
		})

		clear_block(frm, 'apps_list_block');
		new AwaitedComponent(frm.get_field('apps_list_block').$wrapper, {
			promise: Promise.all([
				apps_fetch,
				installed_apps_fetch
			]),
			onload: ([apps_res, installed_apps_res]) => {
				let apps = remap(apps_res.message, (d) => {
					let tag = d.update_available ? 'Update Availabe' : (d.hash ? d.hash.substring(0,7) : "")
					let tag_type = tag ? 'indicator-pill blue' : '' 
					return {
						title: d.title,
						message: d.repository + '/' + d.repository + ':' + d.branch,
						tag: tag,
						tag_type: tag_type
					};
				});
				let installable_apps = installed_apps_res.message;
				new SectionHead(frm.get_field('apps_list_block').$wrapper, {
					title: 'Apps',
					description: 'Apps available on your bench',
					button: {
						title: 'Add App',
						onclick: async () => {
							let app_sources = [];
							for (let installed_app of installable_apps) {
								for(let app_source of installed_app.sources) {
									app_sources.push(app_source.name)
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
									for(let selection of selections) {
										let app_source = await frappe.db.get_doc("App Source", selection);
										// Add the selected app to bench using api
										frappe.call({
											method: 'press.api.bench.add_app',
											args: {
												name: frm.docname,
												source: app_source.name,
												app: app_source.app
											}
										}).then(() => {
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
			}
		})

		clear_block(frm, 'recent_deploys_block');
		new AwaitedComponent(frm.get_field('recent_deploys_block').$wrapper, {
			promise: recent_deploys_fetch,
			onload: (recent_deploys_res) => {
				let recent_deploys = remap(recent_deploys_res.message, (d) => {
					return {
						message: 'Deployed On ' + format_date_time(d.creation, 1, 1),
					};
				});
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
			}
		})

		// sec: Sites
		clear_block(frm, 'sites_block');
		new AwaitedComponent(frm.get_field('sites_block').$wrapper, {
			promise: versions_fetch,
			onload: (versions_res) => {
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
				});
				new ListComponent(frm.get_field('sites_block').$wrapper, {
					data: sites,
					template: title_with_sub_text_tag_and_button_template,
					onclick: (i) => {
						// TODO: use frm methods for this redirects
						window.location.href = `/app/site/${sites[i].title}`;
					},
				});
			}
		})

		// sec: Deploys
		clear_block(frm, 'deploys_section_block');
		new AwaitedComponent(frm.get_field('deploys_section_block').$wrapper, {
			promise: deploy_logs_fetch,
			onload: (deploys_logs_res) => {
				let deploys_log = remap(deploys_logs_res.message, (d) => {
					let tag_color = '';
					if(d.status === 'Pending') tag_color = 'yellow';
					if(d.status === 'Failure') tag_color = 'red';
					if(d.status === 'Undelivered') tag_color = 'gray';
					return {
						title: "Deploy on " + format_date_time(d.creation, 1, 1),
						message: d.apps, // break this array into string
						tag: d.status === 'Success' ? '' : d.status,
						tag_type: `${ d.status === 'Success' ? '' : ('indicator-pill ' + tag_color)}`,
						name: d.name,
						type: d.name
					}
				});
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
								message: d.output || "No output"
							}
						});
		
						new ListComponent(wrapper, {
							data: deploy_lines,
							template: title_with_text_area_template
						})
					}
				})
		
			}
		})
		
		// sec: Jobs
		clear_block(frm, 'jobs_block');
		new AwaitedComponent(frm.get_field('jobs_block').$wrapper, {
			promise: jobs_logs_fetch,
			onload: (jobs_logs_res) => {
				let jobs_log = remap(jobs_logs_res.message, (d) => {
					let tag_color = '';
					if(d.status === 'Pending') tag_color = 'yellow';
					if(d.status === 'Failure') tag_color = 'red';
					if(d.status === 'Undelivered') tag_color = 'gray';
					return {
						title: d.job_type,
						message: d.end,
						tag: d.status === 'Success' ? '' : d.status,
						tag_type: `${ d.status === 'Success' ? '' : ('indicator-pill ' + tag_color)}`,
						name: d.name,
						type: d.name
					}
				})
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
								message: d.output || "No output"
							}
						});
		
						new ListComponent(wrapper, {
							data: job_lines,
							template: title_with_text_area_template
						})
					}
				})
			}
		})

		frm.doc.created_on = frm.doc.apps[0].creation;

		if (frm.is_new()) {
			frm.call('validate_dependencies');
		}
	},
});