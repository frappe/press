// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {
	onload: function (frm) {
        if(frm.get_field("setup_wizard_complete")) {
            show_block_with_events(frm, 'site_activation_block', site_activation);
        }

        // Overview
        show_data(frm, daily_usage, 'daily_usage_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});
        // show_data(frm, recent_activity, 'recent_activity_block', 'press.api.site.overview');
        show_data(frm, site_plan, 'plan_block', 'press.api.site.get_plans');
        show_data(frm, site_info, 'site_info_block', 'press.api.site.overview');
        // show_data(frm, site_apps, 'site_apps_block', 'press.api.site.overview');
        show_data(frm, site_domain, 'site_domain_block', 'press.api.site.overview');

        // Analytics
        show_data(frm, usage_counter, 'usage_counter_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});
        show_data(frm, uptime, 'uptime_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});
        show_data(frm, requests, 'requests_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});
        show_data(frm, cpu_usage, 'cpu_usage_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});
        show_data(frm, background_jobs, 'background_jobs_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});
        show_data(frm, background_jobs_cpu_usage, 'background_jobs_cpu_usage_block', 'press.api.analytics.daily_usage', {name: frm.docname, timezone: moment.tz.guess()});

        // Backups & Restore
        show_data(frm, site_backups, 'site_backups_block', 'press.api.site.backups');
        show_block_with_events(frm, 'restore_migrate_and_reset_block', restore_migrate_and_reset);

        // Site Config
        show_data(frm, site_config, 'site_config_block', 'press.api.site.site_config');

        // Jobs
        show_data(frm, site_jobs, 'jobs_block', 'press.api.site.jobs');

        // Logs
        show_data(frm, site_logs, 'logs_block', 'press.api.site.logs');

        // Activity
        show_data(frm, site_activity, 'activity_block', 'press.api.site.activities');

        frappe.call({
            method: 'press.api.site.overview',
            args: {name: frm.docname, limit: 3}
        }).then((res) => {
            let recent_activities = res.message.recent_activity;
            let installed_apps = res.message.installed_apps;
            
            var recent_activities_data = [];
            for(var ra of recent_activities) {
                recent_activities_data.push({
                    title: ra.action + ' by ' + ra.owner,
                    message: ra.creation
                })
            }
            
            var installed_apps_data = [];
            for(var ia of installed_apps) {
                installed_apps_data.push({
                    title: ia.title,
                    message: ia.repository + '/' + ia.repository + ':' + ia.branch,
                    tag: ia.hash.substring(0,7),
                    tag_type: 'indicator-pill blue'
                })
            }

            new ListComponent(frm.get_field('recent_activity_block').$wrapper, {'data': recent_activities_data, 'template': title_with_message_and_tag_template});            
            new ListComponent(frm.get_field('site_apps_block').$wrapper, {'data': installed_apps_data, 'template': title_with_message_and_tag_template});
        })

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
	refresh: function (frm) {
		frm.dashboard.set_headline_alert(
			`<div class="container-fluid">
				<div class="row">
					<div class="col-sm-4">CPU Usage: ${frm.doc.current_cpu_usage}%</div>
					<div class="col-sm-4">Database Usage: ${frm.doc.current_database_usage}%</div>
					<div class="col-sm-4">Disk Usage: ${frm.doc.current_disk_usage}%</div>
				</div>
			</div>`
		);
		frm.add_web_link(`https://${frm.doc.name}`, __('Visit Site'));
		frm.add_web_link(
			`/dashboard/sites/${frm.doc.name}`,
			__('Visit Dashboard')
		);

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
	},
});

// custom html

let site_activation = (events) => {
    return `
        <div class="flex flex-row justify-between align-items-center">
            <div class="d-flex flex-row">
                <strong class="mr-3">Site Activation</strong>
                <p>Please login and complete the setup wizard on your site. Analytics will be collected only after setup is complete.</p>
            </div>
            `
                + standard_button({
                    name: 'login',
                    title: 'Login',
                    tag: 'btn-primary',
                    events: events,
                    onclick: () => {
                        frappe.msgprint(__('Login'));
                    }
                })
                +
            `
        </div>
    `;
}

let daily_usage = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let recent_activity = (message) => {
    let recent_activity = message.recent_activity;
    return iterate_list(recent_activity, (activity) => {
        return standard_title_with_message_and_tag(activity.action + ' by ' + activity.owner, activity.creation);
    });
}

let site_plan = (message) => {
    if(message.length > 0) {
        return `
            <div class="">
                Plan: ${message}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No plan</p>
            </div>
        `;
    }
}

let site_info = (message, events) => {
    let info = message.info;
    return `
        <div class="d-flex flex-row">
            <div class="d-flex flex-column w-50 mr-4">
            ` 
                + standard_input_with_title('Site owner', info.owner.first_name)
                + standard_input_with_title('Created on', info.created_on)
                + standard_input_with_title('Last deploy', info.last_deploy) 
                +
            `
            </div>
            <div class="d-flex flex-column w-50">
            `
                + standard_action_with_title_and_message({
                    title: 'Deactivate Site',
                    message: "The site will go inactive and won't be publicly accessible",
                    btn_name: 'deactivate-site',
                    events: events,
                    action: () => {
                        frappe.msgprint(__('Deactivate Site'));
                    }
                })
                + standard_action_with_title_and_message({
                    title: 'Drop Site',
                    message: "Once you drop site your site, there is no going back",
                    btn_name: 'drop-site',
                    btn_type: 'danger',
                    events: events,
                    action: () => {
                        frappe.msgprint(__('Drop Site'));
                    }
                })
                +
            `
            </div>
        </div>
    `;
}

let site_apps = (message, events) => {
    let installed_apps = message.installed_apps;
    return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-row">
                <p>Apps installed on your site</p>
                `
                    + standard_button({
                        name: 'add-app',
                        title: 'Add App',
                        tag: 'btn-light ml-auto mb-4',
                        events: events,
                        onclick: () => {
                            frappe.msgprint(__('Add App'));
                        }
                    })
                    +
                `
            </div>
            <div>
                `
                    + iterate_list(installed_apps, (app) => {
                        return standard_title_with_message_and_tag(app.title, app.app + '/' + app.repository + ':' + app.branch, app.hash.substring(0,7), "indicator-pill blue");
                    })
                    +
                `
            </div>
        </div>
    `;
}

let site_domain = (message, events) => {
    let domains = message.domains;
    return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-row">
                <p>Domains pointing to your site</p>
                `
                    + standard_button({
                        name: 'add-domain',
                        title: 'Add Domain',
                        tag: 'btn-light ml-auto mb-4',
                        events: events,
                        onclick: () => {
                            frappe.msgprint(__('Add Domain'));
                        }
                    })
                    +
                `
            </div>
            <div>
                `
                    + iterate_list(domains, (domain) => {
                        return standard_title_with_message_and_tag(null, domain.domain, domain.primary ? "Primary": "", "indicator-pill green")
                    })
                    +
                `
            </div>
        </div>
    `;
}

let usage_counter = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let uptime = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let requests = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let cpu_usage = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let background_jobs = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let background_jobs_cpu_usage = (message) => {
    let data = message.data;
    if(data.length > 0) {
        return `
            <div class="">
                Daily Usage: ${data}
            </div>
        `;
    } else {
        return `
            <div class="d-flex justify-content-center">
                <p class="m-3 mb-4">No data yet</p>
            </div>
        `;
    }
};

let site_backups = (message, events) => {
    let backups = message;
    return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-row">
                <p>Backups are enabled and are scheduled to run every six hours.</p>
                `
                    + standard_button({
                        name: 'schedule-backup-now',
                        title: 'Schedule a backup now',
                        tag: 'btn-light ml-auto mb-4',
                        events: events,
                        onclick: () => {
                            frappe.msgprint(__('Schedule a backup now'));
                        }
                    })
                    +
                `
            </div>
            <div>
                `
                    + iterate_list(backups, (backup) => {
                        return standard_title_with_message_and_tag(null, backup.creation);
                    })
                    +
                `
            </div>
        </div>
    `;
}

let restore_migrate_and_reset = (events) => {
    return `
        <div class="d-flex flex-column">
            `
                + standard_action_with_title_and_message({
                    title: 'Restore',
                    message: "Restore your database using a previous backup",
                    btn_name: 'restore-database',
                    btn_title: 'Restore Database',
                    btn_type: 'light',
                    events: events,
                    action: () => {
                        frappe.msgprint(__('Restore Database'));
                    }
                })
                + standard_action_with_title_and_message({
                    title: 'Migrate',
                    message: "Run bench migrate command on your database.",
                    btn_name: 'migrate-database',
                    btn_title: 'Migrate Database',
                    btn_type: 'light',
                    events: events,
                    action: () => {
                        frappe.msgprint(__('Migrate Database'));
                    }
                })
                + standard_action_with_title_and_message({
                    title: 'Reset',
                    message: "Reset your database to a clean state.",
                    btn_name: 'reset-database',
                    btn_title: 'Reset Database',
                    btn_type: 'danger',
                    events: events,
                    action: () => {
                        frappe.msgprint(__('Reset Database'));
                    }
                })
                + standard_action_with_title_and_message({
                    title: 'Clear Cache',
                    message: "Clear your site's cache",
                    btn_name: 'clear-cache',
                    btn_title: 'Clear Cache',
                    btn_type: 'danger',
                    events: events,
                    action: () => {
                        frappe.msgprint(__('Clear Cache'));
                    }
                })
                +
            `
        </div>
    `;
}

let site_config = (message, events) => {
    let configs = message;
    return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-row justify-between">
                <span>Add and update key value pairs to your site's site_config.json</span>
                `
                    + standard_button({
                        name: 'edit-config',
                        title: 'Edit Config',
                        events: events,
                        onclick: () => {
                            frappe.msgprint(__('Edit Config'));
                        }
                    })
                    +
                `
            </div>
            <div class="d-flex flex-row justify-between">
                <div class="control-value like-disabled-input w-50">
                    <pre> site_config.js {`
                        + iterate_list(configs, (config) => {
                            return `
                                <p>${config}</p>
                            `;
                        })
                        +
                    `}</pre>
                </div>
            </div>
        </div>
    `;
}

let site_jobs = (message) => {
    let jobs = message;
    var focused_job = 0;
    return `
        <div class="d-flex flex-row">
            <div class="d-flex flex-column w-25 mr-4">
                <span class="mb-4">History of jobs that ran on your site</span>
                <div>
                    `
                        + iterate_list(jobs, (job) => {
                            var pill_color = "";
                            if(job.status == "Success") {
                                pill_color = "green";
                            } else if(job.status == "Undelivered") {
                                pill_color = "gray"
                            }

                            return standard_title_with_message_and_tag(job.job_type, job.creation, job.status, "indicator-pill " + pill_color);
                        })
                        +
                    `
                </div>
            </div>
            <div style="border-left:0.2px solid #DFDAD9"></div>
            <div class="d-flex flex-column ml-3">
                    <h5>${jobs[focused_job].job_type}</h5>
                    <span>Completed in ${jobs[focused_job].duration}</span>
            </div>
        </div>
    `;
}

let site_logs = (message) => {
    let logs = message;
    var focused_job = 0;
    return `
        <div class="d-flex flex-row">
            <div class="d-flex flex-column w-25 mr-4">
                <span class="mb-4">Available Logs for your site</span>
                <div>
                    `
                        + iterate_list(logs, (log) => {
                            return standard_title_with_message_and_tag(log.name, log.created);
                        })
                        +
                    `
                </div>
            </div>
            <div style="border-left:0.2px solid #DFDAD9"></div>
            <div class="d-flex flex-column ml-3">
                    <h5>${logs[focused_job].name}</h5>
            </div>
        </div>
    `;
}

let site_activity = (message) => {
    let activities = message;
    return `
        <div class="d-flex flex-row">
            <div class="d-flex flex-column w-50 mr-4">
                <span class="mb-4">Log of activities performed on your site</span>
                <div>
                    `
                        + iterate_list(activities, (activity) => {
                            return standard_title_with_message_and_tag(activity.action + ' by ' + activity.owner, activity.creation);
                        })
                        +
                    `
                </div>
            </div>
            <div style="border-left:0.2px solid #DFDAD9"></div>
        </div>
    `;
}

// render components
function standard_input_with_title(title, value, restricted = true) {
    if(!value) {
        value = "";
    }
    return `
        <div class="d-flex flex-column mb-3">
            <div class="clearfix">
                <label class="control-label">${title}</label>
            </div>
            <div class="control-input-wrapper">
                <div class="control-value like-disabled-input bold">
                    <span>${value}</span>
                </div>
            </div>
        </div>
    `;
}

function standard_action_with_title_and_message({title, message, btn_type = 'light', btn_name, btn_title = title, events, action}) {
    return `
        <div class="d-flex flex-column mb-3">
            <span class="font-weight-bold">${title}</span>
            <div class="d-flex flex-row justify-between mt-2">
                <p>${message}</p>
                `
                    + standard_button({
                        name: btn_name,
                        title: btn_title,
                        tag: 'btn-' + btn_type,
                        events: events,
                        onclick: action
                    })
                    +
                `
            </div>
        </div>
    `;
}

function standard_title_with_message_and_tag(title, message, tag, tag_type = "") {
    return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-column">
                <h5>${title ? title : ""}</h5>
            </div>
            <div class="d-flex flex-row justify-between">
                <p>${message ? message : ""}</p>
                <p class="${tag_type}">${tag ? tag : ""}</p>
            </div>
        </div>
    `;
}

function standard_button({name, title, tag = 'btn-light', events = [], onclick = () => {frappe.msgprint(__('Button click'))}}) {
    events.push({name: name, action: onclick});
    return `
        <button class="${name} btn ${tag}">
            <span>${title}</span>
        </button>
    `;
}

function iterate_list(data, template) {
    var html = '';

    for(var i = 0; i < data.length; i++) {
        html += template(data[i]);
        if(i != data.length - 1 ) html += '<hr class="mt-1">';
    }
    return html;
}

function show_data(frm, template, block, method, args = {name: frm.docname}) {
	let events = [];
    frappe
		.call({
            method: method,
            args: args
        })
		.then((res) => {
            show_block(frm, block, template(res.message, events), events);
		});
}

function show_block_with_events(frm, block, html) {
    let events = [];
    show_block(frm, block, html(events), events)
}

function show_block(frm, block, html, events = []) {
    let wrapper = frm.get_field(block).$wrapper;
    wrapper.empty();
    wrapper.append(`${html}`);

    for(let event of events) {
        wrapper.find("." + event.name).on('click', event.action);
    }
}

function title_with_message_and_tag_template(data) {
    let title = data.title || '';
    let message = data.message || '';
    let tag = data.tag || '';
    let tag_type = data.tag_type || '';

    return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-column">
                <h5>${title || ""}</h5>
            </div>
            <div class="d-flex flex-row justify-between">
                <p>${message || ""}</p>
                <p class="${tag_type}">${tag || ""}</p>
            </div>
        </div>
    `;
}

class ListComponent {
    constructor(parent, df) {
        this.parent = parent;
        this.df = df || {};

        this.make();
    }

    make() {
        this.wrapper = $(`<div class="form-column">`).appendTo(this.parent);

        let html = iterate_list(this.df.data, this.df.template);
        this.wrapper.append(`${html}`);
    }

    iterate_list(data, template) {
        var html = '';
    
        for(var i = 0; i < data.length; i++) {
            html += template(data[i]);
            if(i != data.length - 1 ) html += '<hr class="mt-1">';
        }
        return html;
    }
}

async function get_data(method) {
    return frappe.call({
            method: method,
            args: args
        });
}