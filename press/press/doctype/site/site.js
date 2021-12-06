// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.require('assets/press/js/ListComponent.js')
frappe.require('assets/press/js/SectionHead.js')
frappe.require('assets/press/js/ActionBlock.js')
frappe.require('assets/press/js/DetailedListComponent.js')
frappe.require('assets/press/js/ChartComponent.js')
frappe.require('assets/press/js/AwaitedComponent.js')
frappe.require('assets/press/js/utils.js')

frappe.ui.form.on('Site', {
	onload: async function (frm) {
		frm.set_query('bench', function () {
			return {
				filters: {
					server: frm.doc.server,
					status: 'Active',
				},
			};
		});
		frm.set_query('host_name', () => {
			return {
				filters: {
					site: frm.doc.name,
					status: 'Active'
				},
			};
		});
	},
	refresh: async function (frm) {
		// frm.dashboard.set_headline_alert(
		// 	`<div class="container-fluid">
		// 		<div class="row">
		// 			<div class="col-sm-4">CPU Usage: ${frm.doc.current_cpu_usage}%</div>
		// 			<div class="col-sm-4">Database Usage: ${frm.doc.current_database_usage}%</div>
		// 			<div class="col-sm-4">Disk Usage: ${frm.doc.current_disk_usage}%</div>
		// 		</div>
		// 	</div>`
		// );
        let site = frm.get_doc();
        let account = await frappe.call({
            method: 'press.api.account.get'
        }).then(resp => resp.message);

        
        frm.add_custom_button(__('Use Dashboard'), () => {
            window.location.href = `/dashboard/sites/${frm.docname}/overview`;
        });
        if (site.status === 'Active') {
            frm.add_custom_button(__('Login as Adminstrator'), () => {
                if(account) {
                    let account = account_res.message;
                    if (site.team === account.team.name) {
                        login_as_admin(site.name);
                    } else {
                        new frappe.ui.Dialog({
                            title: 'Login as Adminstrator',
                            fields: [
                                {
                                    label: 'Please enter reason for this login.',
                                    fieldname: 'reason',
                                    fieldtype: 'Small Text'
                                }
                            ],
                            primary_action_label: 'Login',
                            primary_action(values) {
                                if (values) {
                                    let reason = values.reason;
                                    console.log(reason);
                                    login_as_admin(site.name, reason);
                                } else {
                                    frappe.throw(__('Reason field should not be empty'))
                                }
                                this.hide();
                            }
                        }).show();                    
                    }
                } else {
                    frappe.throw(__("could'nt retrieve account. Check Error Log for more information"));
                }
            });
        }
        frm.add_custom_button(__('Visit Site'), () => {
            window.location.href = `https://${frm.doc.name}`;
        });

		[
			[__('Backup'), 'backup'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => { frm.call(method).then((r) => frm.refresh()) },
				__('Actions')
			);
		});
		[
			[__('Archive'), 'archive'],
			[__('Cleanup after Archive'), 'cleanup_after_archive'],
			[__('Migrate'), 'migrate'],
			[__('Reinstall'), 'reinstall'],
			[__('Restore'), 'restore_site'],
			[__('Restore Tables'), 'restore_tables'],
			[__('Clear Cache'), 'clear_cache'],
			[__('Update'), 'schedule_update'],
			[__('Deactivate'), 'deactivate'],
			[__('Activate'), 'activate'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frappe.confirm(
						`Are you sure you want to ${label.toLowerCase()} this site?`,
						() => frm.call(method).then((r) => frm.refresh())
					);
				},
				__('Actions')
			);
		});
		[
			[__('Suspend'), 'suspend'],
			[__('Unsuspend'), 'unsuspend'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frappe.prompt(
						{ fieldtype: 'Data', label: 'Reason', fieldname: 'reason', reqd: 1 },
						({ reason }) => {
							frm.call(method, { reason }).then((r) => frm.refresh());
						},
						__('Provide Reason')
					);
				},
				__('Actions')
			);
		});
		frm.toggle_enable(['host_name'], frm.doc.status === 'Active');

        // data fetch
        let overview_res = await frappe.call({
            method: 'press.api.site.overview',
            args: {name: frm.docname}
        });
        let analytics_res = {message: ''};
        let daily_usage_res = {message: ''};
        if (frm.doc.status === 'Active') {
            if (location.hostname === 'frappecloud.com' || 
            location.hostname === 'staging.frappe.cloud') { // TODO: this is just a hack, need to find a better way
                analytics_res = await frappe.call({
                    method: 'press.api.analytics.get',
                    args: {
                        name: frm.docname,
                        timezone: moment.tz.guess()
                    },
                });
                daily_usage_res = await frappe.call({
                    method: 'press.api.analytics.daily_usage',
                    args: {
                        name: frm.docname,
                        timezone: moment.tz.guess()
                    }                
                })
            }
        }
        let backups_res = await frappe.call({
            method: 'press.api.site.backups',
            args: {name: frm.docname}
        });
        let logs_res = await frappe.call({
            method: 'press.api.site.logs',
            args: {name: frm.docname}
        });
        let activities_res = await frappe.call({
            method: 'press.api.site.activities',
            args: {name: frm.docname}
        });

        // data remaps
        let recent_activities = remap(overview_res.message.recent_activity, (d) => {
            return {
                title: d.action + ' by ' + d.owner,
                message: format_date_time(d.creation, 1, 1)
            };
        });
        let installed_apps = remap(overview_res.message.installed_apps, (d) => {
            return {
                title: d.title,
                message: d.repository + '/' + d.repository + ':' + d.branch,
                tag: d.hash.substring(0,7),
                tag_type: 'indicator-pill blue'
            };
        });
        let domains = remap(overview_res.message.domains, (d) => {
            return {
                message: d.domain,
                tag: d.primary ? "primary" : "",
                tag_type: d.primary ? 'indicator-pill green': ""
            };
        });
        let backups = remap(backups_res.message, (d) => {
            return {
                message: format_date_time(d.creation, 1, 1)
            }
        });
        let logs = remap(logs_res.message, (d) => {
            return {
                title: d.name,
                message: format_date_time(d.created, 1, 1),
                line: d.line
            }
        });
        let activities = remap(activities_res.message, (d) => {
            return {
                title: d.action + ' by ' + d.owner,
                message: format_date_time(d.creation, 1, 1)
            }
        });
        
        let daily_usage_data = daily_usage_res.message || '';
        let usage_counter_data = analytics_res.message.usage_counter || '';
        let uptime_data = analytics_res.message.uptime || '';
        let request_count_data = analytics_res.message.request_count || '';
        let request_cpu_time_data = analytics_res.message.request_cpu_time || '';
        let job_count_data = analytics_res.message.job_count || '';
        let job_cpu_time_data = analytics_res.message.job_cpu_time || '';

        // render
        
        // // tab: Overview 
        clear_block(frm, 'site_activation_block');
        if(site.status === 'Active' && !site.setup_wizard_complete) {
            new ActionBlock(frm.get_field('site_activation_block').$wrapper, {
                title: 'Site Activation',
                description: 'Please login and complete the setup wizard on your site. Analytics will be collected only after setup is complete',
                button: {
                    title: 'Login',
                    onclick: async () => {
                        frappe.call({
                            method: 'press.api.site.login',
                            args: { name: frm.docname }
                        }).then((sid) => {
                            if(sid) {
                                // TODO: this is not working need to fix it
                				window.open(`https://${site.name}/desk?sid=${sid}`, '_blank');
                            }
                        })
                    },
                    tag: 'primary'
                }
            })
        }

        clear_block(frm, 'update_alert_block');
        let update_information = (await frappe.call({
            method: 'press.api.site.check_for_updates',
            args: { name: frm.docname }
        })).message;
        if(update_information) {
            if(update_information.update_available && 
                ['Active', 'Inactive', 'Suspended'].includes(site.status)) {
                    new ActionBlock(frm.get_field('update_alert_block').$wrapper, {
                        title: 'Update Available',
                        description: 'A new update is available for your site. Would you like to update your site now?',
                        button: {
                            title: 'Show updates',
                            onclick: async () => {
                                frappe.call({
                                    method: 'press.api.site.update',
                                    args: {
                                        name: frm.docname,
                                        skip_failing_patches: false // this should be handled properly
                                    }
                                }).then(() => {
                                    frappe.msgprint(__('Site update scheduled successfully!'))
                                })
                            },
                            tag: 'primary'
                        }
                    })
                }
        }

        var data = '';
        var plan_limit = '';
        var values = '';
        
        var chart_data = '';
        
        if(daily_usage_data) {
            data = daily_usage_data.data;
			plan_limit = daily_usage_data.plan_limit;
            values = data.map(d => d.value / 1000000);

            chart_data = {
                labels: format_chart_date(data),
                datasets: [{ values }],
                // show daily limit marker if usage crosses 50%
                yMarkers: values.some(value => value > plan_limit / 2)
                    ? [{ label: 'Daily CPU Time Limit', value: plan_limit }]
                    : null
            }
        }
        clear_block(frm, 'daily_usage_block');
        new ChartComponent(frm.get_field('daily_usage_block').$wrapper, {
            title: 'Daily Usage',
            data: chart_data,
            type: 'line',
            button: {
                title: 'All analytics',
                onclick: () => {
                    frm.scroll_to_field('usage_counter_block');
                }
            },
            colors: ['blue']
        });

        // sec: Recent Activity
        clear_block(frm, 'recent_activity_block');
        new SectionHead(frm.get_field('recent_activity_block').$wrapper, {
            title: 'Recent Activity',
            button: {
                title: 'All activity',
                onclick: () => {
                    frm.scroll_to_field('activity_block');
                }
            }
        })
        new ListComponent(frm.get_field('recent_activity_block').$wrapper, {
            data: recent_activities, 
            template: title_with_message_and_tag_template
        });            

        // sec: Site Info
        clear_block(frm, 'site_info_block');
        frm.set_value('created_on', format_date_time(frm.doc['creation'], 1));
        frm.set_value('last_deployed', format_date_time(frm.doc['creation'], 1));        // TODO: get the actual value
        new ActionBlock(frm.get_field('site_info_block').$wrapper, {
            title: 'Deactivate Site',
            description: "The site will go inactive and won't be publicly accessible",
            button: {
                title: 'Deactivate Site',
                onclick: () => {
                    frappe.confirm(
                        `Are you sure you want to deactivate this site?`,
                        () => frm.call('deactivate').then((r) => frm.refresh())
                    );
                }
            }
        });
        new ActionBlock(frm.get_field('site_info_block').$wrapper, {
            title: 'Drop Site',
            description: "Once you drop site your site, there is no going back",
            button: {
                title: 'Drop Site',
                onclick: () => {
                    frappe.confirm(
                        `Are you sure you want to drop this site?`,
                        () => frm.call('archive').then((r) => frm.refresh())
                    );
                },
                tag: 'danger'
            }
        });

        // sec: Apps
        clear_block(frm, 'site_apps_block');
        new SectionHead(frm.get_field('site_apps_block').$wrapper, {
            title: 'Apps', 
            description: 'Apps installed on your site',
            button: {
                title: 'Add App', 
                onclick:  async () => {
                    let available_apps = (await frappe.call({
                        method: 'press.api.site.available_apps',
                        args: { name: frm.docname }
                    })).message;

                    let apps = [];
                    for(let app of available_apps) {
                        apps.push(app.app);
                    }
                    if(apps.length > 0) {
                        new frappe.ui.form.MultiSelectDialog({
                            doctype: "App",
                            target: frm,
                            setters: {

                            },
                            add_filters_group: 0,
                            get_query() {
                                return {
                                    filters: { name: ['in', apps] }
                                }
                            },
                            async action(selections) {
                                for(let selection of selections) {
                                    frappe.call({
                                        method: 'press.api.site.install_app',
                                        args: {
                                            name: frm.docname,
                                            app: selection
                                        }
                                    }).then(() => {
                                        window.location.reload();
                                    })
                                }
                            }
                        });
                    } else {
                        frappe.msgprint(__("No apps available to install"));
                    }
                }
            }
        });
        new ListComponent(frm.get_field('site_apps_block').$wrapper, {
            data: installed_apps, 
            template: title_with_message_and_tag_template
        });

        // sec: Domains
        clear_block(frm, 'site_domain_block');
        new SectionHead(frm.get_field('site_domain_block').$wrapper, {
            title: 'Domains', 
            description: 'Domains pointing to your site',
            button: {
                title: 'Add Domain', 
                onclick: async () => {
                    let d = new frappe.ui.Dialog({
                        title: 'Add Domain',
                        fields: [
                            {
                                label: 'Domain Name ( eg: www.example.com )',
                                fieldname: 'domain',
                                fieldtype: 'Data'
                            }
                        ],
                        primary_action_label: 'Varify DNS',
                        primary_action(values) {
                            d.hide();
                            if(values['domain']) {
                                let domain = values['domain']
                                frm.call('add_domain', { domain }).then((r) => frm.refresh());
                            } else {
                                frappe.throw(__('Domain cannot be empty'));
                            }
                        }
                    });
                    d.show();
                }
            }
        });
        new ListComponent(frm.get_field('site_domain_block').$wrapper, {
            data: domains, 
            template: title_with_message_and_tag_template
        });

        // tab Anlytics
        chart_data = '';
        if(usage_counter_data) {
            values = usage_counter_data.map(d => d.value / 1000000);

            chart_data = {
                labels: format_chart_date(data),
                datasets: [{ values }],
				// show daily limit marker if usage crosses 50%
				yMarkers: values.some(value => value > plan_limit / 2)
					? [{ label: 'Daily CPU Time Limit', value: plan_limit }]
					: null
            }
        }
        clear_block(frm, 'usage_counter_block');
        new ChartComponent(frm.get_field('usage_counter_block').$wrapper, {
            title: 'Usage Counter',
            data: chart_data,
            type: 'line',
            colors: ['purple'],
            button: {
                title: 'View detailed logs',
                onclick: () => {
                    frm.scroll_to_field('logs_block');
                }
            }
        });

        chart_data = '';
        if(uptime_data) {
            chart_data = {
                labels: format_chart_date(uptime_data),
				datasets: [{ values: uptime_data.map(d => d.value) }]
            }
        }
        clear_block(frm, 'uptime_block');
        new ChartComponent(frm.get_field('uptime_block').$wrapper, {
            title: 'Uptime',
            data: chart_data,
            type: 'mixed-bars'
        });

        chart_data = '';
        if(request_count_data) {
            chart_data = {
                labels: format_chart_date(request_count_data),
				datasets: [{ values: request_count_data.map(d => d.value) }]
            }
        }
        clear_block(frm, 'requests_block');
        new ChartComponent(frm.get_field('requests_block').$wrapper, {
            title: 'Requests',
            data: chart_data,
            type: 'line',
            colors: ['green']
        });

        chart_data = '';
        if(request_cpu_time_data) {
            chart_data = {
                labels: format_chart_date(request_cpu_time_data),
				datasets: [{ values: request_cpu_time_data.map(d => d.value / 1000000) }]
            }
        }
        clear_block(frm, 'cpu_usage_block');
        new ChartComponent(frm.get_field('cpu_usage_block').$wrapper, {
            title: 'CPU Usage',
            data: chart_data,
            type: 'line',
            colors: ['yellow']
        });

        chart_data = '';
        if(job_count_data) {
            chart_data = {
                labels: format_chart_date(job_count_data),
				datasets: [{ values: job_count_data.map(d => d.value) }]
            }
        }
        clear_block(frm, 'background_jobs_block');
        new ChartComponent(frm.get_field('background_jobs_block').$wrapper, {
            title: 'Background Jobs',
            data: chart_data,
            type: 'line',
            colors: ['red']
        });

        chart_data = '';
        if(job_cpu_time_data) {
            chart_data = {
                labels: format_chart_date(job_cpu_time_data),
				datasets: [{ values: job_cpu_time_data.map(d => d.value / 1000000) }]
            }
        }
        clear_block(frm, 'background_jobs_cpu_usage_block');
        new ChartComponent(frm.get_field('background_jobs_cpu_usage_block').$wrapper, {
            title: 'Background Jobs CPU Usage',
            data: chart_data,
            type: 'line',
            colors: ['blue']
        });
        // tab: Backup & Restore

        // sec: Backup
        clear_block(frm, 'site_backups_block');
        new SectionHead(frm.get_field('site_backups_block').$wrapper, {
            title: 'Backup',
            button: {
                title: 'Schedule a Backup',
                onclick: () => {
                    frm.call('backup').then((r) => frm.refresh());
                }
            }
        });
        new ListComponent(frm.get_field('site_backups_block').$wrapper, {
            data: backups,
            template: title_with_message_and_tag_template
        });

        // sec: Restore, Migrate and Reset
        clear_block(frm, 'restore_migrate_and_reset_block');
        new SectionHead(frm.get_field('restore_migrate_and_reset_block').$wrapper, {
            title: 'Restore Migrate & Reset'
        });
        new ActionBlock(frm.get_field('restore_migrate_and_reset_block').$wrapper, {
            title: 'Restore',
            description: "Restore your database using a previous backup",
            button: {
                title: 'Restore Database',
                onclick: () => {
					frappe.confirm(
						`Are you sure you want to restore this site?`,
						() => frm.call('restore_site').then((r) => frm.refresh())
					);
                }
            }
        });
        new ActionBlock(frm.get_field('restore_migrate_and_reset_block').$wrapper, {
            title: 'Migrate',
            description: "Run bench migrate command on your database",
            button: {
                title: 'Migrate Database',
                onclick: () => {
					frappe.confirm(
						`Are you sure you want to migrate this site?`,
						() => frm.call('migrate').then((r) => frm.refresh())
					);
                }
            }
        });
        new ActionBlock(frm.get_field('restore_migrate_and_reset_block').$wrapper, {
            title: 'Reset',
            description: "Reset your database to a clean state",
            button: {
                title: 'Reset Database',
                onclick: () => {
					frappe.confirm(
						`Are you sure you want to reset this site?`,
						() => frm.call('reinstall').then((r) => frm.refresh())
					);
                },
                tag: 'danger'
            }
        });
        new ActionBlock(frm.get_field('restore_migrate_and_reset_block').$wrapper, {
            title: 'Clear Cache',
            description: "Clear your site's cache",
            button: {
                title: 'Clear Cache',
                onclick: () => {
					frappe.confirm(
						`Are you sure you want to clear the cache of this site?`,
						() => frm.call('clear_cache').then((r) => frm.refresh())
					);
                }
            }
        });

        // tab: Jobs

        // sec: Jobs

        clear_block(frm, 'jobs_block');
        new AwaitedComponent(frm.get_field('jobs_block').$wrapper, {
            promise: frappe.call({
                method: 'press.api.site.jobs',
                args: {name: frm.docname}
            }),
            onload: (jobs_res) => {
                let jobs = remap(jobs_res.message, (d) => {
                    let tag_color = '';
                    if(d.status === 'Pending') tag_color = 'yellow';
                    if(d.status === 'Failure') tag_color = 'red';
                    if(d.status === 'Undelivered') tag_color = 'gray';
                    return {
                        title: d.job_type,
                        message: format_date_time(d.creation, 1, 1),
                        tag: d.status === 'Success' ? '' : d.status,
                        tag_type: `${ d.status === 'Success' ? '' : ('indicator-pill ' + tag_color)}`,        
                        name: d.name,
                        type: d.job_type,
                        duration: d.duration,
                        start: d.start,
                        output: d.output
                    }
                });
                new DetailedListComponent(frm.get_field('jobs_block').$wrapper, {
                    title: 'Jobs',
                    description: 'History of jobs that ran on your site',
                    data: jobs,
                    template: title_with_message_and_tag_template,
                    onclick: async (index, wrapper) => {
                        new AwaitedComponent(wrapper, {
                            promise: frappe.db.get_list('Agent Job Step', {
                                filters: {'agent_job': ['in', jobs[index].name]},
                                fields: ['step_name', 'duration', 'output', 'status'],
                                order_by: 'creation'
                            }),
                            onload: (job_steps) => {
                                job_steps = remap(job_steps, (d) => {
                                    return {
                                        title: d.step_name,
                                        message: d.output || 'No output'
                                    }
                                })
                                new SectionHead(wrapper, {
                                    title: jobs[index].type,
                                    description: 'Created on ' + format_date_time(jobs[index].start, 1, 1) + ' executed in ' + jobs[index].duration
                                });
                                new ListComponent(wrapper, {
                                    data: job_steps,
                                    template: title_with_text_area_template
                                });
                            },
                        })
                    }
                });
            }
        })

        // tab: Logs

        clear_block(frm, 'logs_block');
        new DetailedListComponent(frm.get_field('logs_block').$wrapper, {
            title: 'Logs',
            description: 'Available Logs for your site',
            data: logs,
            template: title_with_message_and_tag_template,
            onclick: async (index, wrapper) => {
                new AwaitedComponent(wrapper, {
                    promise: frappe.call({
                        method: 'press.api.site.log',
                        args: {
                            name: frm.docname,
                            log: logs[index].title
                        }
                    }),
                    onload: (log) => {
                        new SectionHead(wrapper, {
                            title: logs[index].title
                        });
                        
                        var log_lines = log.message[logs[index].title].split('\n');
                        log_lines = remap(log_lines, (d) => {
                            return {
                                message: d
                            }
                        });
                        new ListComponent(wrapper, {
                            data: log_lines,
                            template: title_with_text_area_template
                        });
                    }
                })
            }
        });

        // tab: Activity

        // sec: Activity

        clear_block(frm, 'activity_block');
        new SectionHead(frm.get_field('activity_block').$wrapper, {
            title: 'Activity',
            description: 'Log of activities performed on your site'
        })

        new ListComponent(frm.get_field('activity_block').$wrapper, {
            data: activities,
            template: title_with_message_and_tag_template
        })
        
        // tab: Settings
	},
});


function login_as_admin(site_name, reason=null) {
    frappe.call({
        method: 'press.api.site.login',
        args: {
            name: site_name,
            reason: reason
        }
    }).then((sid) => {
        if (sid) {
            window.open(`https://${site_name}/desk?sid=${sid}`, '_blank');
        }
    }, (error) => {
        console.log(error);
        frappe.throw(__(`An error occurred!!`));
    })
}