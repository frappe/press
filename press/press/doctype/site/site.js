// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {
	onload: function (frm) {
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
        if(frm.get_field("setup_wizard_complete")) {
            show_site_activation_block(frm);
        } else {
            // TODO: hide site_activation_block
        }

        // Overview tab blocks
        show_daily_usage_chart(frm);
        show_recent_activity(frm);
        show_site_plane(frm);
        show_site_info(frm);
        show_site_apps(frm);
        show_site_domains(frm);

        // Analytics tab blocks

        // Backups & restore blocks
        show_site_backups(frm);
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

function show_site_activation_block(frm) {
    var wrapper = frm.get_field("site_activation_block").$wrapper;
    wrapper.empty();
    wrapper.append(`
        <div class="alert alert-info">
            <div class="items-start px-4 md:px-5 py-3.5 text-base rounded-md flex">
                <div class="w-full ml-2">
                    <div class="flex flex-col md:items-baseline md:flex-row">
                        <div>
                            <strong class="mr-2">
                                Site Activation
                            </strong>
                            <span>
                                Please login and complete the setup wizard on your site. Analytics will be collected only after setup is complete.
                            </span>
                            <span class="ml-5">
                                <button class="btn btn-primary">Login</button>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);
}

function show_daily_usage_chart(frm) {
    let site_name = frm.doc.name;
    let local_timezone = moment.tz.guess();

    var wrapper = frm.get_field("daily_usage_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.analytics.daily_usage",
        args: {
            name: site_name,
            timezone: local_timezone
         },
         callback: function(r) {
            let data = r.message.data;
            if(data.length > 0) {
                populate_daily_usage_chart(wrapper, data);
            } else {
                wrapper.append(`
                    <div class="my-3">
                        No data yet
                    </div>
                `)
            }
         }
    });
}

function show_recent_activity(frm) {
    let site_name = frm.doc.name;

    var wrapper = frm.get_field("recent_activity_block").$wrapper;
    wrapper.empty();

    wrapper.append(`
        <span>
            History of recent activities performed on your site
        </span>
    `)

    frappe.call({
        method: "press.api.site.overview",
        args: {
            name: site_name
         },
         callback: function(r) {
            let recent_activity = r.message.recent_activity;
            populate_recent_activity_list(wrapper, recent_activity);
         }
    });
}

function show_site_plane(frm) {
    let site_name = frm.doc.name;

    var wrapper = frm.get_field("plan_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.site.get_plans",
        args: {
            name: site_name
        },
        callback: function(r) {
            let data = r.message;
            if(data.length > 0) {

            } else {
                wrapper.append(`
                    <div>
                        Plan not set yet
                    </div>
                `);
            }
        }
    });
}

function show_site_info(frm) {
    let site_name = frm.doc.name;

    var wrapper = frm.get_field("site_info_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.site.overview",
        args: {
            name: site_name
        },
        callback: function(r) {
            if(r.message.info) {
                var info = r.message.info;
                wrapper.append(`
                    <div>
                        <span>
                            General information about your site
                        </span>
                        <div class="mt-3">
                            <span class="my-2 mr-2">
                                ` + "Owned By: " + info.owner.first_name + `
                            </span>
                            <span class="m-2">
                                ` + "Created On: " + info.created_on + `
                            </span>
                            <span class="m-2">
                                ` + "Last Deployed: " + info.last_deployed + `
                            </span>
                        </div>
                        <div class="mt-3">
                            <strong>
                                Deactivate Site
                            </strong> </br>
                            <span class="mr-3">
                                The site will go inactive and won't be publicly accessible
                            </span>
                            <button>
                                Deactivate Site
                            </button>
                        </div>
                        <div class="mt-3">
                            <strong>
                                Drop Site
                            </strong> </br>
                            <span class="mr-3">
                                Once you drop site your site, there is no going back
                            </span>
                            <button>
                                Drop Site
                            </button>
                        </div>
                    </div>
                `)
            }
        }
    });
}

function show_site_apps(frm) {
    let site_name = frm.doc.name;

    var wrapper = frm.get_field("site_apps_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.site.overview",
        args: {
            name: site_name
        },
        callback: function(r) {
            let installed_apps = r.message.installed_apps;
            wrapper.append(`
                <span class="mr-4">
                    Apps installed on your site
                </span>
                <button class="mb-2">
                    Add App
                </button>
            `);
            if(installed_apps.length > 0) {
                for(var i = 0; i < installed_apps.length; i++){
                    wrapper.append(`
                        <li>
                            <span class="mr-3">
                                ` + installed_apps[i].title + `
                            </span>
                            <span class="mr-3">
                                ` + installed_apps[i].repository + "/" + installed_apps[i].branch + `
                            </span>
                            <span class="mr-3">
                                ` + installed_apps[i].hash.substring(0,7) + `
                            </span>
                        </li>
                    `)
                }
            } else {
                wrapper.append(`
                    <div>
                        No apps installed
                    </div>
                `);
            }
        }
    });
}

function show_site_domains(frm) {

    let site_name = frm.doc.name;

    var wrapper = frm.get_field("site_domain_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.site.overview",
        args: {
            name: site_name
        },
        callback: function(r) {
            let domains = r.message.domains;
            wrapper.append(`
                <span class="mr-4">
                    Domains pointing to your site
                </span>
                <button class="mb-2">
                    Add Domain
                </button>
            `);
            if(domains.length > 0) {
                for(var i = 0; i < domains.length; i++){
                    wrapper.append(`
                        <li>
                            <span class="mr-3">
                                ` + domains[i].domain + `
                            </span>
                            <span class="mr-3">
                                ` + "primary: " + domains[i].primary +  `
                            </span>
                        </li>
                    `)
                }
            } else {
                wrapper.append(`
                    <div>
                        Not yet set
                    </div>
                `);
            }
        }
    });
}

function show_site_backups(frm) {
    let site_name = frm.doc.name;

    var wrapper = frm.get_field("site_backups_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.site.backups",
        args: {
            name: site_name
        },
        callback: function(r) {
            console.log(r);
            wrapper.append(`
                <span class="mr-4">
                    Backups are enabled and are scheduled to run every six hours.
                </span>
                <button class="mb-2">
                    Schedule a backup now
                </button>
            `);
            let backups = r.message;
            for(var i = 0; i < backups.length; i++) {
                wrapper.append(`
                    <li>
                        ` + "Backup on: " + backups[i].creation + `
                    </li>
                `);
            }
        }
    });
}

function populate_daily_usage_chart(wrapper, data) {
    // TODO: make a chart
    for (let i = 0; i < data.length; i++) {
        wrapper.append(`<li> data: ` + data[i].date + ' max: '+ data[i].max + `</li>`);
    }
}

function populate_recent_activity_list(wrapper, recent_activity) {
    for(let i = 0; i < recent_activity.length; i++) {
        wrapper.append(`
            <li> ` + recent_activity[i].action +
            " by " + recent_activity[i].owner +
            " | " + recent_activity[i].creation +
            ` </li>
        `);
    }
}